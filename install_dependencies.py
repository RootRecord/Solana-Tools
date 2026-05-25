#!/usr/bin/env python
from __future__ import annotations

import importlib.util
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path


APP_NAME = "Solana Tools"
MIN_PYTHON = (3, 10)
REQUIRED_IMPORTS = {
    "base58": "base58",
    "requests": "requests",
    "solana": "solana",
    "solders": "solders",
    "spl": "spl-token helpers from solana-py",
}
OPTIONAL_IMPORTS = {
    "PyInstaller": "pyinstaller",
}
NODE_DOWNLOAD_URL = "https://nodejs.org/en/download"


def is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def repo_root() -> Path:
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def missing_imports(imports: dict[str, str]) -> list[str]:
    return [package for module, package in imports.items() if importlib.util.find_spec(module) is None]


def prompt_yes_no(question: str, default: bool = False) -> bool:
    suffix = " [Y/n]: " if default else " [y/N]: "
    answer = input(question + suffix).strip().lower()
    if not answer:
        return default
    return answer in {"y", "yes"}


def run(command: list[str], *, cwd: Path | None = None) -> None:
    print("> " + " ".join(command), flush=True)
    subprocess.check_call(command, cwd=str(cwd) if cwd else None)


def ensure_python_version() -> bool:
    current = sys.version_info[:2]
    if current >= MIN_PYTHON:
        print(f"Python {sys.version.split()[0]} OK.", flush=True)
        return True

    print(f"Python {MIN_PYTHON[0]}.{MIN_PYTHON[1]}+ is required. Current: {sys.version.split()[0]}", flush=True)
    if is_frozen():
        print("The packaged exe can run without installing Python, but source scripts need Python installed.", flush=True)
    if prompt_yes_no("Open the Python download page now?"):
        webbrowser.open("https://www.python.org/downloads/")
    return False


def command_path(command: str) -> str:
    return shutil.which(command) or shutil.which(f"{command}.cmd") or ""


def ensure_node_tools() -> bool:
    node = command_path("node")
    npm = command_path("npm")
    if not node or not npm:
        print("Node.js and npm are required for TypeScript SDK actions.", flush=True)
        if prompt_yes_no("Open the Node.js download page now?"):
            webbrowser.open(NODE_DOWNLOAD_URL)
        return False

    run([node, "--version"])
    run([npm, "--version"])
    return True


def package_json_path() -> Path | None:
    candidates = [repo_root() / "package.json", Path(__file__).resolve().parent / "package.json"]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def ensure_node_dependencies() -> None:
    package_json = package_json_path()
    if not package_json:
        print("No package.json found; skipping TypeScript SDK dependency install.", flush=True)
        return

    package_root = package_json.parent
    node_modules = package_root / "node_modules"
    if node_modules.exists():
        print("Node SDK dependencies appear to be installed.", flush=True)
        return

    if not ensure_node_tools():
        return

    if prompt_yes_no("Install TypeScript SDK dependencies with npm now?"):
        run([command_path("npm"), "install"], cwd=package_root)
    else:
        print("Skipped TypeScript SDK dependency installation.", flush=True)


def main() -> int:
    print(f"{APP_NAME} dependency check", flush=True)
    print("=" * 40, flush=True)

    if is_frozen():
        print("Running from packaged exe. Normal dashboard use does not require system Python packages.", flush=True)
        print("This helper is mainly for users who want to run source scripts or rebuild the exe.", flush=True)

    if not ensure_python_version():
        return 1

    missing_required = missing_imports(REQUIRED_IMPORTS)
    missing_optional = missing_imports(OPTIONAL_IMPORTS)

    if not missing_required:
        print("Required runtime dependencies are installed.", flush=True)
    else:
        print("Missing required packages:", ", ".join(missing_required), flush=True)
        if prompt_yes_no("Install required packages now?"):
            requirements = repo_root() / "requirements.txt"
            if requirements.exists():
                run([sys.executable, "-m", "pip", "install", "-r", str(requirements)])
            else:
                run([sys.executable, "-m", "pip", "install", *missing_required])
        else:
            print("Skipped required dependency installation.", flush=True)

    if missing_optional:
        print("Optional build package missing:", ", ".join(missing_optional), flush=True)
        if prompt_yes_no("Install optional exe build tools now?"):
            run([sys.executable, "-m", "pip", "install", *missing_optional])

    ensure_node_dependencies()

    print("Dependency check finished.", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
