#!/usr/bin/env python
from __future__ import annotations

import ast
import os
import queue
import re
import runpy
import subprocess
import sys
import threading
import traceback
from dataclasses import dataclass
from pathlib import Path
from tkinter import BOTH, END, LEFT, RIGHT, VERTICAL, Y, BooleanVar, StringVar, Tk, filedialog, messagebox
from tkinter import ttk
from tkinter.scrolledtext import ScrolledText


APP_NAME = "Solana Tools"


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


def run_script_mode(script_path: str) -> int:
    try:
        runpy.run_path(script_path, run_name="__main__")
        return 0
    except SystemExit as exc:
        return int(exc.code or 0)
    except Exception:
        traceback.print_exc()
        return 1


def parse_description(path: Path) -> str:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        return (ast.get_docstring(tree) or "").splitlines()[0].strip()
    except Exception:
        return path.stem.replace("_", " ").title()


def parse_env_names(path: Path) -> tuple[str, ...]:
    text = path.read_text(encoding="utf-8")
    names = set(re.findall(r'env(?:_int|_float|_bool|_list)?\(\s*["\']([A-Z0-9_]+)["\']', text))
    names.update(re.findall(r'pubkey\(\s*["\']([A-Z0-9_]+)["\']', text))
    names.update(re.findall(r'keypair\(\s*["\']([A-Z0-9_]+)["\']', text))
    ignored = {"MESSAGE", "ENCODING"}
    return tuple(sorted(name for name in names if name not in ignored))


def discover_actions() -> list[Action]:
    root = bundled_root()
    candidates: list[Path] = []
    for folder_name in ["isolated_scripts", "Roots"]:
        folder = root / folder_name
        if folder.exists():
            candidates.extend(path for path in folder.rglob("*.py") if "__pycache__" not in path.parts)

    excluded = {"config.py", "__init__.py"}
    actions: list[Action] = []
    for path in sorted(candidates):
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
        self.output_queue: queue.Queue[str] = queue.Queue()
        self.status_var = StringVar()
        self.send_transaction_var = BooleanVar(value=False)
        self.stdin_var = StringVar()

        self._build_ui()
        self._populate_actions()
        self._refresh_status()
        self._pump_output()

    def _build_ui(self) -> None:
        self.root.columnconfigure(0, weight=0)
        self.root.columnconfigure(1, weight=1)
        self.root.rowconfigure(1, weight=1)

        toolbar = ttk.Frame(self.root, padding=8)
        toolbar.grid(row=0, column=0, columnspan=2, sticky="ew")

        ttk.Label(toolbar, text=APP_NAME, font=("Segoe UI", 16, "bold")).pack(side=LEFT, padx=(0, 16))
        ttk.Label(toolbar, textvariable=self.status_var).pack(side=LEFT, padx=(0, 16))
        ttk.Button(toolbar, text="Reload .env", command=self.reload_env).pack(side=LEFT, padx=4)
        ttk.Button(toolbar, text="Open .env", command=self.open_env_file).pack(side=LEFT, padx=4)
        ttk.Checkbutton(toolbar, text="SEND_TRANSACTION=true", variable=self.send_transaction_var).pack(side=LEFT, padx=12)

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
        ttk.Button(controls, text="Run Selected", command=self.run_selected).pack(side=LEFT, padx=(0, 6))
        ttk.Button(controls, text="Stop", command=self.stop_process).pack(side=LEFT, padx=6)
        ttk.Button(controls, text="Clear Terminal", command=self.clear_terminal).pack(side=LEFT, padx=6)
        ttk.Button(controls, text="Copy Terminal", command=self.copy_terminal).pack(side=LEFT, padx=6)

        stdin_frame = ttk.Frame(right)
        stdin_frame.grid(row=3, column=0, sticky="ew", pady=(8, 0))
        stdin_frame.columnconfigure(0, weight=1)
        ttk.Entry(stdin_frame, textvariable=self.stdin_var).grid(row=0, column=0, sticky="ew")
        ttk.Button(stdin_frame, text="Send Input", command=self.send_input).grid(row=0, column=1, padx=(6, 0))

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

    def open_env_file(self) -> None:
        env_path = app_root() / ".env"
        if not env_path.exists():
            example = app_root() / ".env.example"
            if example.exists():
                env_path.write_text(example.read_text(encoding="utf-8"), encoding="utf-8")
            else:
                env_path.write_text("", encoding="utf-8")
        os.startfile(env_path)  # type: ignore[attr-defined]

    def run_selected(self) -> None:
        action = self.selected_action()
        if action is None:
            messagebox.showinfo(APP_NAME, "Select an action first.")
            return
        if self.process and self.process.poll() is None:
            messagebox.showwarning(APP_NAME, "Another action is already running.")
            return

        runner_args = self._runner_args(action)
        env = os.environ.copy()
        env.update(self.env_values)
        env["PYTHONUNBUFFERED"] = "1"
        env["SEND_TRANSACTION"] = "true" if self.send_transaction_var.get() else env.get("SEND_TRANSACTION", "false")

        self.write_terminal(f"\n> {action.label}\n")
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
        threading.Thread(target=self._read_process_output, daemon=True).start()

    def _runner_args(self, action: Action) -> list[str]:
        if is_frozen():
            return [sys.executable, "--run-script", str(action.path)]
        return [sys.executable, str(Path(__file__).resolve()), "--run-script", str(action.path)]

    def _read_process_output(self) -> None:
        assert self.process and self.process.stdout
        for line in self.process.stdout:
            self.output_queue.put(line)
        return_code = self.process.wait()
        self.output_queue.put(f"\n[process exited with code {return_code}]\n")

    def _pump_output(self) -> None:
        while True:
            try:
                self.write_terminal(self.output_queue.get_nowait())
            except queue.Empty:
                break
        self.root.after(80, self._pump_output)

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

    def send_input(self) -> None:
        if not self.process or self.process.poll() is not None or not self.process.stdin:
            return
        self.process.stdin.write(self.stdin_var.get() + "\n")
        self.process.stdin.flush()
        self.stdin_var.set("")


def main() -> int:
    if len(sys.argv) >= 3 and sys.argv[1] == "--run-script":
        return run_script_mode(sys.argv[2])

    root = Tk()
    Dashboard(root)
    root.mainloop()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
