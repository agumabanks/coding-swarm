#!/usr/bin/env python3
import subprocess, sys, venv
from pathlib import Path

ROOT = Path(__file__).parent.parent
PKG = ROOT / "packages"

def run(cmd, cwd=None):
    print(">>", " ".join(cmd))
    subprocess.run(cmd, check=True, cwd=cwd)

def ensure_venv(venv_dir: Path):
    if not venv_dir.exists():
        print("Creating venv:", venv_dir)
        venv.EnvBuilder(with_pip=True).create(venv_dir)
    return venv_dir / ("Scripts" if sys.platform.startswith("win") else "bin") / "python"

def main():
    print("🚀 Bootstrapping Coding Swarm monorepo...")
    py = ensure_venv(ROOT / ".venv")

    run([str(py), "-m", "pip", "install", "-U", "pip", "setuptools", "wheel"])

    order = ["core", "agents", "orchestrator", "plugins", "api", "cli"]
    for name in order:
        pkg_dir = PKG / name
        if pkg_dir.exists():
            run([str(py), "-m", "pip", "install", "-e", str(pkg_dir)])

    print("✅ Bootstrap complete!")
    print(f"Activate venv:\n  source {ROOT}/.venv/bin/activate  # or .venv\\Scripts\\activate on Windows")

if __name__ == "__main__":
    main()
