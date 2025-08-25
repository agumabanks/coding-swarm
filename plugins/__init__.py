import importlib
import pathlib
import sys
from typing import Dict, Any
import yaml

# Global registry for agents, commands, and plugin metadata
REGISTRY: Dict[str, Dict[str, Any]] = {
    "agents": {},
    "commands": {},
    "plugins": {},
}


def load_plugins(plugin_dir: str | pathlib.Path | None = None) -> None:
    """Discover and load plugins from ``plugin_dir``.

    Each plugin lives in a subdirectory with a ``plugin.yml`` manifest file.
    The manifest must define an ``entry_point`` of the form ``module:function``.
    The callable is invoked with ``REGISTRY`` so the plugin may register
    agents or commands.
    """
    base = pathlib.Path(plugin_dir or pathlib.Path(__file__).resolve().parent)
    if not base.exists():
        return

    # Ensure plugin packages are importable
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))

    for manifest in base.glob("*/plugin.yml"):
        meta = yaml.safe_load(manifest.read_text()) or {}
        name = meta.get("name", manifest.parent.name)
        REGISTRY["plugins"][name] = meta
        entry = meta.get("entry_point")
        if not entry:
            continue
        try:
            module_name, func_name = entry.split(":", 1)
            module = importlib.import_module(module_name)
            func = getattr(module, func_name)
            func(REGISTRY)
        except Exception as exc:  # pragma: no cover - logging only
            print(f"Failed to load plugin {name}: {exc}")

