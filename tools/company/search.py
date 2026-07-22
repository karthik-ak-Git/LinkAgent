"""Search companies tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier


class SearchCompanies(BaseTool):
    name = "search_companies"
    capability = "company"
    tier = ToolTier.SEARCH
    best_for = ["Finding LinkedIn company pages by keyword"]
    input_schema = {
        "type": "object",
        "properties": {
            "keywords": {
                "type": "string",
                "description": "Search keywords (e.g. 'fintech', 'anthropic')",
            },
        },
        "required": ["keywords"],
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        keywords = inputs["keywords"]

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor

        extractor = await get_authenticated_extractor()
        result = await extractor.search_companies(keywords)

        return ToolResult(data=result)
