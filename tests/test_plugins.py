from plugins import REGISTRY, load_plugins


def test_load_plugins_from_registry(tmp_path):
    # Copy example plugin to temporary directory
    plugin_src = tmp_path / "plugins"
    plugin_src.mkdir()
    example_src = plugin_src / "example"
    example_src.mkdir()
    (example_src / "__init__.py").write_text("")
    (example_src / "plugin.yml").write_text(
        """name: example
version: 0.1.0
description: test plugin
entry_point: example.plugin:register
"""
    )
    # create minimal module implementing register
    (example_src / "plugin.py").write_text(
        """from typing import Dict, Any

class Example:
    pass

def register(registry: Dict[str, Dict[str, Any]]) -> None:
    registry['agents']['example'] = Example
"""
    )
    # registry.json referencing example plugin
    registry_file = plugin_src / "registry.json"
    registry_file.write_text('[{"name": "example", "path": "example"}]')

    # Load plugins from temp directory
    REGISTRY['agents'].clear()
    REGISTRY['commands'].clear()
    REGISTRY['plugins'].clear()
    load_plugins(plugin_src)

    assert 'example' in REGISTRY['plugins']
    assert 'example' in REGISTRY['agents']
