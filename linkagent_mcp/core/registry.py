"""
Extractor registry — maps domains to extractors, generates MCP tools dynamically.

Usage:
    from linkagent_mcp.core.registry import registry
    from linkagent_mcp.sites.linkedin import register_linkedin_extractors

    register_linkedin_extractors(registry)  # or auto_discover()

    tools = registry.list_tools()           # -> List[Tool]
    result = registry.extract(tool_name, client, **kwargs)
"""

from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Type

from ..cdp.client import CDPClient


@dataclass
class ExtractorEntry:
    """A registered extractor with its metadata."""
    name: str                          # Tool name (e.g. "linkedin_feed")
    extractor_class: Type              # The BaseExtractor subclass
    domain: str                        # Domain this handles (e.g. "linkedin.com")
    description: str                   # Tool description for MCP
    input_schema: dict = field(default_factory=dict)  # JSON Schema for parameters
    navigate_url: str = ""             # URL to navigate to before extraction (optional)
    url_patterns: list[str] = field(default_factory=list)  # URL patterns to match


class Registry:
    """
    Central registry for all site extractors.

    Supports:
    - Registering extractors with metadata
    - Auto-discovering site modules
    - Generating MCP tool definitions
    - Dispatching tool calls to the right extractor
    """

    def __init__(self):
        self._extractors: dict[str, ExtractorEntry] = {}
        self._domains: dict[str, list[str]] = {}  # domain -> [tool_names]

    def register(
        self,
        name: str,
        extractor_class: Type,
        domain: str,
        description: str,
        input_schema: Optional[dict] = None,
        navigate_url: str = "",
        url_patterns: Optional[list[str]] = None,
    ):
        """Register an extractor."""
        entry = ExtractorEntry(
            name=name,
            extractor_class=extractor_class,
            domain=domain,
            description=description,
            input_schema=input_schema or {"type": "object", "properties": {}},
            navigate_url=navigate_url,
            url_patterns=url_patterns or [],
        )
        self._extractors[name] = entry
        if domain not in self._domains:
            self._domains[domain] = []
        self._domains[domain].append(name)

    def list_tools(self) -> list[dict]:
        """Generate MCP tool definitions from registered extractors."""
        tools = []
        for entry in self._extractors.values():
            tools.append({
                "name": entry.name,
                "description": entry.description,
                "inputSchema": entry.input_schema,
            })
        return tools

    def get_entry(self, tool_name: str) -> Optional[ExtractorEntry]:
        """Get a registered extractor entry by tool name."""
        return self._extractors.get(tool_name)

    def find_extractor_for_url(self, url: str) -> Optional[ExtractorEntry]:
        """Find the best extractor for a given URL."""
        for entry in self._extractors.values():
            if any(p in url for p in entry.url_patterns):
                return entry
        return None

    def get_domains(self) -> list[str]:
        """List all registered domains."""
        return list(self._domains.keys())

    async def extract(self, tool_name: str, client: CDPClient, **kwargs) -> dict:
        """Dispatch an extraction call to the right extractor."""
        entry = self._extractors.get(tool_name)
        if not entry:
            return {"error": f"Unknown tool: {tool_name}"}

        extractor = entry.extractor_class(client)

        # Navigate if needed and URL doesn't match
        if entry.navigate_url:
            current_url = await client.get_url()
            url_matches = any(p in current_url for p in entry.url_patterns)
            if not url_matches:
                await client.navigate(entry.navigate_url)

        try:
            return await extractor.extract(**kwargs)
        except Exception as e:
            return {"error": f"Extraction failed: {str(e)}"}


# Global registry instance
registry = Registry()
