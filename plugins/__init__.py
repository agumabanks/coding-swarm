import importlib
import json
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


def load_plugins(
    plugin_dir: str | pathlib.Path | None = None,
    registry_path: str | pathlib.Path | None = None,
) -> None:
    """Discover and load plugins from ``plugin_dir``.

    If a ``registry.json`` file is present it will be used to determine which
    plugin directories to load.  Otherwise all subdirectories containing a
    ``plugin.yml`` manifest are loaded.  The manifest must define an
    ``entry_point`` of the form ``module:function``.  The callable is invoked
    with ``REGISTRY`` so the plugin may register agents or commands.
    """
    base = pathlib.Path(plugin_dir or pathlib.Path(__file__).resolve().parent)
    if not base.exists():
        return

    registry_file = pathlib.Path(registry_path or base / "registry.json")

    # Ensure plugin packages are importable
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))

    plugin_dirs: list[pathlib.Path] = []

    if registry_file.exists():
        try:
            entries = json.loads(registry_file.read_text())
            for entry in entries:
                if isinstance(entry, str):
                    plugin_dirs.append(base / entry)
                elif isinstance(entry, dict):
                    plugin_dirs.append(base / entry.get("path", ""))
        except Exception as exc:  # pragma: no cover - logging only
            print(f"Failed to read plugin registry: {exc}")

    if not plugin_dirs:  # Fallback to directory scan
        plugin_dirs = [p.parent for p in base.glob("*/plugin.yml")]

    for plugin_path in plugin_dirs:
        manifest = plugin_path / "plugin.yml"
        if not manifest.exists():
            continue
        meta = yaml.safe_load(manifest.read_text()) or {}
        name = meta.get("name", plugin_path.name)
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

