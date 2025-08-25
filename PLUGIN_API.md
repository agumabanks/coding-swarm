# Plugin API

Coding Swarm can be extended with third-party plugins. Plugins allow new agents
and commands to be registered without modifying the core orchestrator.

## Directory layout

Plugins live under the top-level `plugins/` directory:

```
plugins/
  my_plugin/
    plugin.yml        # manifest
    __init__.py
    plugin.py         # Python implementation
```

## Manifest

Each plugin must provide a `plugin.yml` manifest with at least the following
fields:

```yaml
name: my-plugin                # human readable name
version: 0.1.0                 # plugin version
entry_point: my_plugin.plugin:register
capabilities:                  # optional capabilities provided
  - greet
config_schema:                 # optional JSON schema for configuration
  type: object
  properties:
    name:
      type: string
      description: Name to greet
```

* `entry_point` references a module and callable using the
  `module:function` format. The callable receives the orchestrator registry and
  registers any agents or commands.

## Registering with the orchestrator

The entry point should define a `register` function that accepts the registry
and inserts any agents or commands. The registry structure looks like:

```
registry = {
  "agents": {"name": AgentClass},
  "commands": {"cmd": callable},
  "plugins": {"name": metadata},
}
```

Example `plugin.py` implementation:

```python
from typing import Dict, Any

class ExampleAgent:
    def greet(self, name: str = "world") -> str:
        return f"hello {name}"

def greet(name: str = "world") -> str:
    return ExampleAgent().greet(name)

def register(registry: Dict[str, Dict[str, Any]]) -> None:
    registry["agents"]["example"] = ExampleAgent
    registry["commands"]["greet"] = greet
```

With this structure in place, external developers can drop new folders into the
`plugins/` directory and have their agents and commands automatically loaded on
startup.
