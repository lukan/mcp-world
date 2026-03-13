"""
run.py — mcp-world entrypoint

Usage:
    python run.py mock_world
    python run.py open-world-mmo   (once built)

The adapter name must match a folder under adapters/ containing adapter.py
with a class that extends BaseAdapter.
"""

import importlib
import sys


ADAPTER_CLASS = {
    "mock_world":     ("adapters.mock_world.adapter",    "MockWorldAdapter"),
    # Add new adapters here as they are built:
    # "open-world-mmo": ("adapters.open_world_mmo.adapter", "OpenWorldMMOAdapter"),
}


def main():
    if len(sys.argv) < 2:
        print("Usage: python run.py <adapter_name>")
        print(f"Available: {', '.join(ADAPTER_CLASS)}")
        sys.exit(1)

    name = sys.argv[1]
    if name not in ADAPTER_CLASS:
        print(f"Unknown adapter: '{name}'")
        print(f"Available: {', '.join(ADAPTER_CLASS)}")
        sys.exit(1)

    module_path, class_name = ADAPTER_CLASS[name]
    module = importlib.import_module(module_path)
    adapter_class = getattr(module, class_name)

    from core.server import WorldMCPServer
    server = WorldMCPServer(adapter_class())
    server.run()


if __name__ == "__main__":
    main()
