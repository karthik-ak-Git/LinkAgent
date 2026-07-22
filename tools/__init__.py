"""
LinkedIn MCP tools package — OpenMontage architecture.

Architecture:
  tools/                Tool package (auto-discovered by ToolRegistry)
    base_tool.py        BaseTool ABC — contract for all LinkedIn tools
    tool_registry.py    ToolRegistry — auto-discovery via pkgutil.walk_packages
    _browser/           Private infra: browser management, context, cookie injection
    _auth/              Private infra: cookie store, fingerprint, health check
    _scraping/          Private infra: extractor, fields, connection detection
    _errors/            Private infra: typed exception hierarchy
    person/             Person tool group (BaseTool subclasses)
    company/            Company tool group
    job/                Job tool group
    messaging/          Messaging tool group
    feed/               Feed tool group

Underscore-prefixed packages are skipped by ToolRegistry — they are
internal infrastructure imported by concrete tool subclasses.
"""

from tools.base_tool import BaseTool, ToolResult, ToolTier, ToolStability
from tools.tool_registry import ToolRegistry, registry

__all__ = ["BaseTool", "ToolResult", "ToolRegistry", "ToolTier", "ToolStability", "registry"]
