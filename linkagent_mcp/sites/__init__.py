"""
Sites package — add new site modules here.

Each site module should:
1. Create a directory under sites/ (e.g. sites/twitter/)
2. Implement extractors subclassing core.BaseExtractor
3. Expose a register(registry) function
4. Be called from auto_discover()
"""

import importlib
import pkgutil
from pathlib import Path

from ..core.registry import Registry


def auto_discover(registry: Registry):
    """
    Auto-discover and register all site modules under sites/.

    Each site module must have a register(registry) function.
    """
    sites_dir = Path(__file__).parent
    for finder, name, ispkg in pkgutil.iter_modules([str(sites_dir)]):
        if ispkg and name != "__pycache__":
            try:
                mod = importlib.import_module(f"linkagent_mcp.sites.{name}")
                if hasattr(mod, "register"):
                    mod.register(registry)
            except Exception as e:
                print(f"Warning: Failed to load site module '{name}': {e}")
