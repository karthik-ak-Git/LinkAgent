"""Search conversations tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier


class SearchConversations(BaseTool):
    name = "search_conversations"
    capability = "messaging"
    tier = ToolTier.SEARCH
    best_for = ["Searching LinkedIn messages by keyword"]
    input_schema = {
        "type": "object",
        "properties": {
            "keywords": {"type": "string", "description": "Keywords to filter conversations"},
            "limit": {
                "type": "integer",
                "description": "Max search-result rows to enumerate (1-50)",
                "default": 20,
            },
        },
        "required": ["keywords"],
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        keywords = inputs["keywords"]
        limit = inputs.get("limit", 20)

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor

        extractor = await get_authenticated_extractor()
        result = await extractor.search_conversations(keywords, limit=limit)

        return ToolResult(data=result)
