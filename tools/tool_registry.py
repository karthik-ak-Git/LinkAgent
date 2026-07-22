"""Tool registry with auto-discovery via pkgutil.walk_packages.

Mirrors OpenMontage's ToolRegistry pattern. Discovers all BaseTool
subclasses in the tools/ package tree, skipping underscore-prefixed
packages which are internal infrastructure.
"""

from __future__ import annotations

import importlib
import inspect
import pkgutil
from types import ModuleType
from typing import Any, Optional

from tools.base_tool import BaseTool, ToolStatus, ToolTier


_SKIP_PACKAGES = frozenset({
    "tools._browser",
    "tools._auth",
    "tools._scraping",
    "tools._errors",
})


class ToolRegistry:
    """Central registry of all LinkedIn MCP tools."""

    def __init__(self) -> None:
        self._tools: dict[str, BaseTool] = {}
        self._discovered: bool = False

    def register(self, tool: BaseTool) -> None:
        if not tool.name:
            raise ValueError("Tool must have a non-empty name")
        self._tools[tool.name] = tool

    def register_module(self, module: ModuleType) -> list[str]:
        registered: list[str] = []
        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls is BaseTool or not issubclass(cls, BaseTool):
                continue
            if cls.__module__ != module.__name__ or inspect.isabstract(cls):
                continue
            tool = cls()
            self.register(tool)
            registered.append(tool.name)
        return registered

    def discover(self, package_name: str = "tools") -> list[str]:
        discovered: list[str] = []
        package = importlib.import_module(package_name)
        package_paths = getattr(package, "__path__", None)
        if package_paths is None:
            return self.register_module(package)

        for module_info in pkgutil.walk_packages(package_paths, f"{package.__name__}."):
            name = module_info.name
            if any(skip in name for skip in _SKIP_PACKAGES):
                continue
            if name.endswith(".base_tool") or name.endswith(".tool_registry"):
                continue
            module = importlib.import_module(name)
            discovered.extend(self.register_module(module))

        self._discovered = True
        return discovered

    def ensure_discovered(self) -> None:
        if not self._discovered:
            self.discover()

    def get(self, name: str) -> Optional[BaseTool]:
        self.ensure_discovered()
        return self._tools.get(name)

    def list_all(self) -> list[str]:
        self.ensure_discovered()
        return list(self._tools.keys())

    def get_by_capability(self, capability: str) -> list[BaseTool]:
        self.ensure_discovered()
        return [t for t in self._tools.values() if t.capability == capability]

    def get_by_tier(self, tier: ToolTier) -> list[BaseTool]:
        self.ensure_discovered()
        return [t for t in self._tools.values() if t.tier == tier]

    def get_available(self) -> list[BaseTool]:
        self.ensure_discovered()
        return [t for t in self._tools.values() if t.get_status() == ToolStatus.AVAILABLE]

    def support_envelope(self) -> dict[str, dict[str, Any]]:
        self.ensure_discovered()
        return {
            name: {
                "name": tool.name,
                "version": tool.version,
                "tier": tool.tier.value,
                "capability": tool.capability,
                "provider": tool.provider,
                "stability": tool.stability.value,
                "status": tool.get_status().value,
                "dependencies": tool.dependencies,
                "capabilities": tool.capabilities,
                "input_schema": tool.input_schema,
                "best_for": tool.best_for,
                "not_good_for": tool.not_good_for,
                "fallback_tools": tool.fallback_tools,
            }
            for name, tool in self._tools.items()
        }


registry = ToolRegistry()
