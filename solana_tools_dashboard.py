#!/usr/bin/env python
from __future__ import annotations

import ast
import os
import queue
import re
import runpy
import shutil
import subprocess
import sys
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, VERTICAL, Y, Canvas, StringVar, Toplevel, Tk, messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


APP_NAME = "Solana Tools"
PLACEHOLDER_PREFIXES = ("replace_with", "account_one", "account_two", "account_three")
BASIC_ENV_FIELDS = ("SOLANA_RPC_URL", "SOLANA_CLUSTER", "SOLANA_ACTIVE_PRIVATE_KEY_BASE58")
SECRET_ENV_NAMES = {"SOLANA_ACTIVE_PRIVATE_KEY_BASE58", "SOLANA_OLD_PRIVATE_KEY_BASE58"}
FIELD_HELP = {
    "SOLANA_RPC_URL": "Solana RPC endpoint. Devnet is fine for testing.",
    "SOLANA_CLUSTER": "devnet or mainnet-beta.",
    "SOLANA_ACTIVE_PRIVATE_KEY_BASE58": "Base58 private key for the wallet that signs actions.",
    "SOLANA_OLD_PRIVATE_KEY_BASE58": "Optional previous authority wallet for authority transfer actions.",
    "ROOTS_MINT_ADDRESS": "Optional token mint used by Roots token actions.",
    "ROOTS_OWNER_WALLET": "Optional owner wallet for Roots token actions.",
    "ROOTS_DESTINATION_WALLET": "Optional destination wallet for mint/transfer actions.",
    "ROOTS_NEW_AUTHORITY": "Optional new authority wallet for authority transfer actions.",
    "INPUT_MINT": "Default input mint for swap/LP actions.",
    "OUTPUT_MINT": "Default output mint for swap/LP actions.",
    "RAW_AMOUNT": "Default raw token amount, in smallest units.",
    "SLIPPAGE_BPS": "Default slippage in basis points. 50 = 0.50%.",
}


@dataclass(frozen=True)
class Action:
    label: str
    category: str
    path: Path
    description: str
    env_names: tuple[str, ...]


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def app_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def bundled_root() -> Path:
    return Path(getattr(sys, "_MEIPASS", app_root())).resolve()


def load_dotenv(root: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for env_path in [Path.cwd() / ".env", root / ".env", app_root() / ".env"]:
        if not env_path.exists():
            continue
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def local_env_path() -> Path:
    return app_root() / ".env"


def example_env_path() -> Path:
    for candidate in [app_root() / ".env.example", bundled_root() / ".env.example"]:
        if candidate.exists():
            return candidate
    return app_root() / ".env.example"


def is_placeholder(value: str) -> bool:
    stripped = value.strip()
    return not stripped or any(stripped.startswith(prefix) for prefix in PLACEHOLDER_PREFIXES)


def env_template_lines() -> list[str]:
    path = example_env_path()
    if path.exists():
        return path.read_text(encoding="utf-8").splitlines()
    return [f"{key}=" for key in BASIC_ENV_FIELDS]


def env_template_keys() -> list[str]:
    keys: list[str] = []
    for line in env_template_lines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key = stripped.split("=", 1)[0].strip()
        if key and key not in keys:
            keys.append(key)
    return keys


def merged_env_values(current: dict[str, str]) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in env_template_lines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, default = stripped.split("=", 1)
        value = current.get(key.strip(), default.strip().strip('"').strip("'"))
        values[key.strip()] = "" if is_placeholder(value) else value
    values.update(current)
    for key, value in list(values.items()):
        if is_placeholder(value):
            values[key] = ""
    return values


def write_env_file(values: dict[str, str]) -> None:
    used: set[str] = set()
    lines: list[str] = []
    for line in env_template_lines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            lines.append(line)
            continue
        key = stripped.split("=", 1)[0].strip()
        used.add(key)
        lines.append(f"{key}={values.get(key, '')}")

    extras = sorted(key for key in values if key not in used)
    if extras:
        lines.extend(["", "# Local custom values"])
        lines.extend(f"{key}={values.get(key, '')}" for key in extras)

    local_env_path().write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def wallet_pubkey_from_private_key(private_key_base58: str) -> str:
    if is_placeholder(private_key_base58):
        return ""
    try:
        import base58
        from solders.keypair import Keypair

        return str(Keypair.from_bytes(base58.b58decode(private_key_base58)).pubkey())
    except Exception:
        return ""


def active_wallet_summary(values: dict[str, str]) -> str:
    wallet = wallet_pubkey_from_private_key(values.get("SOLANA_ACTIVE_PRIVATE_KEY_BASE58", ""))
    rpc = values.get("SOLANA_RPC_URL", "(not set)")
    cluster = values.get("SOLANA_CLUSTER", "(not set)")
    if wallet:
        return f"Active wallet: {wallet}\nCluster: {cluster}\nRPC: {rpc}"
    return f"Active wallet: could not be derived from SOLANA_ACTIVE_PRIVATE_KEY_BASE58\nCluster: {cluster}\nRPC: {rpc}"


def run_script_mode(script_path: str) -> int:
    try:
        path = Path(script_path)
        if path.suffix != ".py":
            raise RuntimeError(f"Unsupported in-process script type: {path.suffix}")
        script_dir = str(path.resolve().parent)
        if script_dir not in sys.path:
            sys.path.insert(0, script_dir)
        runpy.run_path(str(path), run_name="__main__")
        return 0
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception:
        traceback.print_exc()
        return 1


def parse_description(path: Path) -> str:
    if path.suffix == ".ts":
        return path.stem.replace("_", " ").title()
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return (ast.get_docstring(tree) or "").splitlines()[0].strip()
    except Exception:
        return path.stem.replace("_", " ").title()


def parse_env_names(path: Path) -> tuple[str, ...]:
    text = path.read_text(encoding="utf-8")
    names = set(re.findall(r'env(?:_int|_float|_bool|_list)?\(\s*["\']([A-Z0-9_]+)["\']', text))
    names.update(re.findall(r'env(?:BigInt|Bool|Int|Json)?\(\s*["\']([A-Z0-9_]+)["\']', text))
    names.update(re.findall(r'pubkey\(\s*["\']([A-Z0-9_]+)["\']', text))
    names.update(re.findall(r'keypair\(\s*["\']([A-Z0-9_]+)["\']', text))
    ignored = {"MESSAGE", "ENCODING"}
    return tuple(sorted(name for name in names if name not in ignored))


class EnvEditorDialog:
    def __init__(self, parent: Tk, values: dict[str, str], *, first_run: bool = False) -> None:
        self.parent = parent
        self.values = dict(values)
        self.saved = False
        self.variables: dict[str, StringVar] = {}
        self.secret_entries: list[ttk.Entry] = []

        self.window = Toplevel(parent)
        self.window.title("Solana Tools .env Setup" if first_run else "Solana Tools .env Editor")
        self.window.geometry("900x720")
        self.window.transient(parent)
        self.window.grab_set()
        self.window.protocol("WM_DELETE_WINDOW", self.cancel)

        self._build(first_run)

    def _build(self, first_run: bool) -> None:
        self.window.columnconfigure(0, weight=1)
        self.window.rowconfigure(1, weight=1)

        intro = ttk.Frame(self.window, padding=12)
        intro.grid(row=0, column=0, sticky="ew")
        intro.columnconfigure(0, weight=1)

        title = "First-Time Setup" if first_run else "Edit Local Settings"
        ttk.Label(intro, text=title, font=("Segoe UI", 14, "bold")).grid(row=0, column=0, sticky="w")
        ttk.Label(
            intro,
            text=(
                "Paste the values Solana Tools should use. Private keys are saved only to your local .env file, "
                "which is ignored by git. At minimum, fill in SOLANA_RPC_URL and SOLANA_ACTIVE_PRIVATE_KEY_BASE58."
            ),
            wraplength=840,
        ).grid(row=1, column=0, sticky="ew", pady=(6, 0))

        canvas = Canvas(self.window, borderwidth=0, highlightthickness=0)
        scroll = ttk.Scrollbar(self.window, orient=VERTICAL, command=canvas.yview)
        form = ttk.Frame(canvas, padding=(12, 0, 12, 0))
        form.bind("<Configure>", lambda _event: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=form, anchor="nw")
        canvas.configure(yscrollcommand=scroll.set)
        canvas.grid(row=1, column=0, sticky="nsew")
        scroll.grid(row=1, column=1, sticky="ns")

        keys = list(BASIC_ENV_FIELDS)
        keys.extend(key for key in env_template_keys() if key not in keys)
        grid_row = 0
        for key in keys:
            value = self.values.get(key, "")
            variable = StringVar(value=value)
            self.variables[key] = variable

            label_text = f"{key} *" if key in BASIC_ENV_FIELDS else key
            ttk.Label(form, text=label_text, width=36).grid(row=grid_row, column=0, sticky="w", pady=3)
            entry = ttk.Entry(form, textvariable=variable, width=78, show="*" if key in SECRET_ENV_NAMES else "")
            entry.grid(row=grid_row, column=1, sticky="ew", pady=3, padx=(8, 0))
            if key in SECRET_ENV_NAMES:
                self.secret_entries.append(entry)
            help_text = FIELD_HELP.get(key, "")
            if help_text:
                ttk.Label(form, text=help_text, foreground="#555555", wraplength=760).grid(
                    row=grid_row + 1,
                    column=1,
                    sticky="w",
                    padx=(8, 0),
                )
                grid_row += 1
            grid_row += 1
        form.columnconfigure(1, weight=1)

        footer = ttk.Frame(self.window, padding=12)
        footer.grid(row=2, column=0, columnspan=2, sticky="ew")
        footer.columnconfigure(0, weight=1)
        ttk.Button(footer, text="Show/Hide Private Keys", command=self.toggle_secrets).grid(row=0, column=0, sticky="w")
        ttk.Button(footer, text="Cancel", command=self.cancel).grid(row=0, column=1, padx=6)
        ttk.Button(footer, text="Save .env", command=self.save).grid(row=0, column=2)

    def toggle_secrets(self) -> None:
        for entry in self.secret_entries:
            entry.configure(show="" if entry.cget("show") == "*" else "*")

    def save(self) -> None:
        values = {key: variable.get().strip() for key, variable in self.variables.items()}
        missing = [key for key in BASIC_ENV_FIELDS if is_placeholder(values.get(key, ""))]
        if missing and not messagebox.askyesno(
            APP_NAME,
            "These first-time setup values are still blank:\n\n"
            + "\n".join(missing)
            + "\n\nSave anyway?",
            parent=self.window,
        ):
            return

        active_key = values.get("SOLANA_ACTIVE_PRIVATE_KEY_BASE58", "")
        if active_key and not wallet_pubkey_from_private_key(active_key):
            messagebox.showerror(
                APP_NAME,
                "SOLANA_ACTIVE_PRIVATE_KEY_BASE58 could not be decoded into a wallet. Please check the pasted private key.",
                parent=self.window,
            )
            return

        self.values = values
        self.saved = True
        self.window.destroy()

    def cancel(self) -> None:
        self.window.destroy()


def discover_actions() -> list[Action]:
    roots = [app_root(), bundled_root()]
    candidates: list[tuple[Path, Path]] = []
    seen: set[str] = set()
    seen_labels: set[str] = set()
    for root in roots:
        for folder_name, extension in [("isolated_scripts", "*.py"), ("Roots", "*.py"), ("ts_actions", "*.ts")]:
            folder = root / folder_name
            if not folder.exists():
                continue
            for path in folder.rglob(extension):
                if "__pycache__" in path.parts or path.name == "common.ts":
                    continue
                label_key = (Path(folder_name) / path.relative_to(folder)).with_suffix("").as_posix()
                if label_key in seen_labels:
                    continue
                key = path.resolve().as_posix().lower()
                if key in seen:
                    continue
                seen.add(key)
                seen_labels.add(label_key)
                candidates.append((root, path))

    excluded = {"config.py", "transaction_confirm.py", "__init__.py"}
    actions: list[Action] = []
    for root, path in sorted(candidates, key=lambda item: item[1].as_posix()):
        if path.name in excluded:
            continue
        relative = path.relative_to(root)
        category = relative.parts[0] if len(relative.parts) == 1 else "/".join(relative.parts[:-1])
        label = relative.with_suffix("").as_posix()
        actions.append(
            Action(
                label=label,
                category=category,
                path=path,
                description=parse_description(path),
                env_names=parse_env_names(path),
            )
        )
    return actions


class Dashboard:
    def __init__(self, root: Tk) -> None:
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("1180x760")
        self.actions = discover_actions()
        self.env_values = load_dotenv(app_root())
        self.current_action: Action | None = None
        self.process: subprocess.Popen[str] | None = None
        self.running_action: Action | None = None
        self.running_mode: str = ""
        self.pending_confirmation_action: Action | None = None
        self.completed_action: Action | None = None
        self.completed_mode: str = ""
        self.completed_return_code: int | None = None
        self.startup_checked = False
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.status_var = StringVar()
        self.stdin_var = StringVar()

        self._build_ui()
        self._populate_actions()
        self._refresh_status()
        self._pump_output()
        self.root.after(350, self.startup_env_check)

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self.root, padding=8)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")

        ttk.Label(toolbar, text=APP_NAME, font=("Segoe UI", 16, "bold")).pack(side=LEFT, padx=(0, 16))
        ttk.Label(toolbar, textvariable=self.status_var).pack(side=LEFT, padx=(0, 16))
        ttk.Button(toolbar, text="Reload .env", command=self.reload_env).pack(side=LEFT, padx=4)
        ttk.Button(toolbar, text="Edit .env", command=self.open_env_editor).pack(side=LEFT, padx=4)
        ttk.Button(toolbar, text="Install/Repair Dependencies", command=self.run_dependency_installer).pack(side=LEFT, padx=4)

        left = ttk.Frame(self.root, padding=(8, 0, 4, 8))
        left.grid(row=1, column=0, sticky="ns")
        left.rowconfigure(0, weight=1)

        self.tree = ttk.Treeview(left, width=42, show="tree")
        self.tree.grid(row=0, column=0, sticky="ns")
        tree_scroll = ttk.Scrollbar(left, orient=VERTICAL, command=self.tree.yview)
        tree_scroll.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll.set)
        self.tree.bind("<<TreeviewSelect>>", self.on_select)

        right = ttk.Frame(self.root, padding=(4, 0, 8, 8))
        right.grid(row=1, column=1, sticky="nsew")
        right.columnconfigure(0, weight=1)
        right.rowconfigure(2, weight=1)

        self.details = ScrolledText(right, height=8, wrap="word", font=("Consolas", 10))
        self.details.grid(row=0, column=0, sticky="ew")
        self.details.configure(state="disabled")

        controls = ttk.Frame(right, padding=(0, 8, 0, 8))
        controls.grid(row=1, column=0, sticky="ew")
        ttk.Button(controls, text="Preview Selected", command=self.preview_selected).pack(side=LEFT, padx=(0, 6))
        self.confirm_button = ttk.Button(controls, text="Confirm/Execute Preview", command=self.confirm_execute, state="disabled")
        self.confirm_button.pack(side=LEFT, padx=6)
        ttk.Button(controls, text="Stop", command=self.stop_process).pack(side=LEFT, padx=6)
        ttk.Button(controls, text="Clear Terminal", command=self.clear_terminal).pack(side=LEFT, padx=6)
        ttk.Button(controls, text="Copy Terminal", command=self.copy_terminal).pack(side=LEFT, padx=6)

        stdin_frame = ttk.Frame(right)
        stdin_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        stdin_frame.columnconfigure(0, weight=1)
        ttk.Entry(stdin_frame, textvariable=self.stdin_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(stdin_frame, text="Send Input", command=self.send_input).grid(row=0, column=1, padx=(6, 0))
        ttk.Button(stdin_frame, text="Enter = Confirm/Send Input", command=self.enter_or_send_input).grid(row=0, column=2, padx=(6, 0))

        self.terminal = ScrolledText(right, wrap="word", font=("Consolas", 10), bg="#07130a", fg="#d4ffd4")
        self.terminal.grid(row=2, column=0, sticky="nsew")

    def _populate_actions(self) -> None:
        parents: dict[str, str] = {}
        for action in self.actions:
            parts = action.category.split("/")
            parent = ""
            path_accum: list[str] = []
            for part in parts:
                path_accum.append(part)
                key = "/".join(path_accum)
                if key not in parents:
                    parents[key] = self.tree.insert(parent, END, text=part, open=True)
                parent = parents[key]
            self.tree.insert(parent, END, text=Path(action.label).name, values=(action.label,))

    def _refresh_status(self) -> None:
        env_path = app_root() / ".env"
        self.status_var.set(f"Actions: {len(self.actions)} | .env: {'found' if env_path.exists() else 'missing'} | Root: {app_root()}")

    def selected_action(self) -> Action | None:
        selected = self.tree.selection()
        if not selected:
            return None
        label = self.tree.item(selected[0], "values")
        if not label:
            return None
        return next((action for action in self.actions if action.label == label[0]), None)

    def on_select(self, _event=None) -> None:
        self.current_action = self.selected_action()
        self.details.configure(state="normal")
        self.details.delete("1.0", END)
        if self.current_action is None:
            self.details.insert(END, "Select an action to see details.")
        else:
            env_lines = "\n".join(f"  - {name}" for name in self.current_action.env_names) or "  (none detected)"
            self.details.insert(
                END,
                f"{self.current_action.description}\n\n"
                f"Script: {self.current_action.path}\n"
                f"Category: {self.current_action.category}\n\n"
                f"Environment variables this script may use:\n{env_lines}\n",
            )
        self.details.configure(state="disabled")

    def reload_env(self) -> None:
        self.env_values = load_dotenv(app_root())
        self._refresh_status()
        self.write_terminal("Reloaded .env\n")

    def startup_env_check(self) -> None:
        if self.startup_checked:
            return
        self.startup_checked = True

        if not self._has_minimum_env():
            messagebox.showinfo(
                APP_NAME,
                "Welcome to Solana Tools.\n\n"
                "Let's set up your local .env file so you do not need to edit anything by hand. "
                "You can paste your RPC URL and active wallet private key in the next window.",
            )
            self.open_env_editor(first_run=True)
            return

        summary = active_wallet_summary(self.env_values)
        if messagebox.askyesno(
            APP_NAME,
            "Solana Tools found an existing .env file.\n\n"
            f"{summary}\n\n"
            "Use this wallet and configuration?",
        ):
            self.write_terminal(f"\n.env confirmed by user.\n{summary}\n")
        else:
            self.open_env_editor(first_run=False)

    def _has_minimum_env(self) -> bool:
        if not local_env_path().exists():
            return False
        return all(not is_placeholder(self.env_values.get(key, "")) for key in BASIC_ENV_FIELDS[:2]) and bool(
            wallet_pubkey_from_private_key(self.env_values.get("SOLANA_ACTIVE_PRIVATE_KEY_BASE58", ""))
        )

    def open_env_editor(self, first_run: bool = False) -> None:
        current_values = merged_env_values(load_dotenv(app_root()))
        dialog = EnvEditorDialog(self.root, current_values, first_run=first_run)
        self.root.wait_window(dialog.window)
        if not dialog.saved:
            return

        write_env_file(dialog.values)
        self.env_values = load_dotenv(app_root())
        self._refresh_status()
        summary = active_wallet_summary(self.env_values)
        self.write_terminal(f"\nSaved .env.\n{summary}\n")
        messagebox.showinfo(APP_NAME, f".env saved.\n\n{summary}")

    def open_env_file(self) -> None:
        env_path = app_root() / ".env"
        if not env_path.exists():
            example = app_root() / ".env.example"
            if example.exists():
                env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                env_path.write_text("", encoding="utf-8")
        os.startfile(env_path)  # type: ignore[attr-defined]

    def preview_selected(self) -> None:
        action = self.selected_action()
        if action is None:
            messagebox.showinfo(APP_NAME, "Select an action first.")
            return
        self.pending_confirmation_action = None
        self._refresh_confirm_button()
        self._run_action(action, mode="preview")

    def confirm_execute(self) -> None:
        action = self.pending_confirmation_action
        if action is None:
            messagebox.showinfo(APP_NAME, "Run Preview Selected first, then review the terminal output.")
            return
        if self.selected_action() != action:
            messagebox.showwarning(APP_NAME, "Select the same action you previewed before executing.")
            return
        if not messagebox.askyesno(
            APP_NAME,
            "Execute this transaction action now?\n\n"
            "Only continue after reviewing the terminal preview, expected fees, mints, amounts, and destination accounts.",
        ):
            self.write_terminal("\n[execution cancelled by user]\n")
            return
        self.pending_confirmation_action = None
        self._refresh_confirm_button()
        self._run_action(action, mode="execute")

    def _run_action(self, action: Action, *, mode: str) -> None:
        if self.process and self.process.poll() is None:
            messagebox.showwarning(APP_NAME, "Another action is already running.")
            return

        try:
            runner_args = self._runner_args(action.path)
        except RuntimeError as exc:
            messagebox.showerror(APP_NAME, str(exc))
            return
        env = os.environ.copy()
        env.update(self.env_values)
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["NODE_PATH"] = self._node_path(env.get("NODE_PATH", ""))
        env["SEND_TRANSACTION"] = "true" if mode == "execute" else "false"
        env["SOLANA_TOOLS_USER_CONFIRMED"] = "true" if mode == "execute" else "false"
        env["SOLANA_TOOLS_RUN_MODE"] = mode

        title = "EXECUTE" if mode == "execute" else "PREVIEW"
        self.write_terminal(f"\n> {title}: {action.label}\n")
        if mode == "preview":
            self.write_terminal("> Review this output. Confirm/Execute is disabled until preview finishes successfully.\n")
        else:
            self.write_terminal("> User confirmed in dashboard. Broadcasting is enabled for this run.\n")
        self.write_terminal(f"> {' '.join(runner_args)}\n\n")

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.process = subprocess.Popen(
            runner_args,
            cwd=str(app_root()),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creationflags,
        )
        self.running_action = action
        self.running_mode = mode
        self.completed_action = None
        self.completed_mode = ""
        self.completed_return_code = None
        threading.Thread(target=self._read_process_output, daemon=True).start()

    def run_dependency_installer(self) -> None:
        if self.process and self.process.poll() is None:
            messagebox.showwarning(APP_NAME, "Another action is already running.")
            return
        installer = bundled_root() / "install_dependencies.py"
        if not installer.exists():
            messagebox.showerror(APP_NAME, "install_dependencies.py was not found.")
            return

        try:
            runner_args = self._runner_args(installer)
        except RuntimeError as exc:
            messagebox.showerror(APP_NAME, str(exc))
            return
        env = os.environ.copy()
        env.update(self.env_values)
        env["PYTHONUNBUFFERED"] = "1"
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        env["NODE_PATH"] = self._node_path(env.get("NODE_PATH", ""))
        self.write_terminal("\n> Install/Repair Dependencies\n")
        self.write_terminal("> Answer prompts with the input box below, then click Send Input.\n")
        self.write_terminal(f"> {' '.join(runner_args)}\n\n")

        creationflags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
        self.process = subprocess.Popen(
            runner_args,
            cwd=str(app_root()),
            env=env,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            creationflags=creationflags,
        )
        self.running_action = None
        self.running_mode = "dependencies"
        self.completed_action = None
        self.completed_mode = ""
        self.completed_return_code = None
        threading.Thread(target=self._read_process_output, daemon=True).start()

    def _runner_args(self, script_path: Path) -> list[str]:
        if script_path.suffix == ".ts":
            return self._typescript_runner_args(script_path)
        if is_frozen():
            return [sys.executable, "--run-script", str(script_path)]
        return [sys.executable, str(Path(__file__).resolve()), "--run-script", str(script_path)]

    def _typescript_runner_args(self, script_path: Path) -> list[str]:
        bin_name = "tsx.cmd" if os.name == "nt" else "tsx"
        local_tsx = app_root() / "node_modules" / ".bin" / bin_name
        if local_tsx.exists():
            return [str(local_tsx), str(script_path)]

        npm_name = "npm.cmd" if os.name == "nt" else "npm"
        npm = shutil.which(npm_name) or shutil.which("npm")
        if npm:
            return [npm, "exec", "--", "tsx", str(script_path)]

        raise RuntimeError("Node/npm was not found. Use Install/Repair Dependencies, install Node.js, then retry.")

    def _node_path(self, existing: str) -> str:
        paths = [str(app_root() / "node_modules"), str(bundled_root() / "node_modules")]
        if existing:
            paths.append(existing)
        return os.pathsep.join(paths)

    def _read_process_output(self) -> None:
        assert self.process and self.process.stdout
        for line in self.process.stdout:
            self.output_queue.put(line)
        return_code = self.process.wait()
        self.completed_action = self.running_action
        self.completed_mode = self.running_mode
        self.completed_return_code = return_code
        self.running_action = None
        self.running_mode = ""
        self.output_queue.put(f"\n[process exited with code {return_code}]\n")

    def _pump_output(self) -> None:
        while True:
            try:
                self.write_terminal(self.output_queue.get_nowait())
            except queue.Empty:
                break
        self._handle_process_completion()
        self.root.after(80, self._pump_output)

    def _handle_process_completion(self) -> None:
        if self.completed_return_code is None:
            return
        action = self.completed_action
        mode = self.completed_mode
        return_code = self.completed_return_code
        self.completed_action = None
        self.completed_mode = ""
        self.completed_return_code = None

        if mode == "preview" and action is not None and return_code == 0:
            self.pending_confirmation_action = action
            self.write_terminal(
                "\n[preview complete]\n"
                "Review the terminal output above, including estimated transaction cost.\n"
                "Click Confirm/Execute Preview to broadcast this same action.\n"
            )
        elif mode == "preview":
            self.pending_confirmation_action = None
            self.write_terminal("\n[preview failed; execution is locked]\n")
        elif mode == "execute":
            self.pending_confirmation_action = None
        self._refresh_confirm_button()

    def write_terminal(self, text: str) -> None:
        self.terminal.insert(END, text)
        self.terminal.see(END)

    def clear_terminal(self) -> None:
        self.terminal.delete("1.0", END)

    def copy_terminal(self) -> None:
        self.root.clipboard_clear()
        self.root.clipboard_append(self.terminal.get("1.0", END))

    def stop_process(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            self.write_terminal("\n[terminate requested]\n")
            self.pending_confirmation_action = None
            self._refresh_confirm_button()

    def send_input(self) -> None:
        if not self.process or self.process.poll() is not None or not self.process.stdin:
            return
        self.process.stdin.write(self.stdin_var.get() + "\n")
        self.process.stdin.flush()
        self.stdin_var.set("")

    def enter_or_send_input(self) -> None:
        if self.process and self.process.poll() is None:
            self.send_input()
            return
        self.confirm_execute()

    def _refresh_confirm_button(self) -> None:
        state = "normal" if self.pending_confirmation_action is not None else "disabled"
        self.confirm_button.configure(state=state)


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--run-script":
        return run_script_mode(sys.argv[2])

    root = Tk()
    Dashboard(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
