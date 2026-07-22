"""Get inbox tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier


class GetInbox(BaseTool):
    name = "get_inbox"
    capability = "messaging"
    tier = ToolTier.SCRAPING
    best_for = ["Listing recent LinkedIn messaging conversations"]
    input_schema = {
        "type": "object",
        "properties": {
            "limit": {
                "type": "integer",
                "description": "Max conversations to load (1-50)",
                "default": 20,
            },
        },
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        limit = inputs.get("limit", 20)

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor

        extractor = await get_authenticated_extractor()
        result = await extractor.get_inbox(limit=limit)

        return ToolResult(data=result)
