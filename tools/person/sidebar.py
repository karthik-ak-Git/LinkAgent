"""Get sidebar profiles tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier


class GetSidebarProfiles(BaseTool):
    name = "get_sidebar_profiles"
    capability = "person"
    tier = ToolTier.SCRAPING
    best_for = ["Extracting recommended profile links from sidebar sections"]
    input_schema = {
        "type": "object",
        "properties": {
            "linkedin_username": {
                "type": "string",
                "description": "LinkedIn username whose sidebar to scrape",
            },
        },
        "required": ["linkedin_username"],
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        linkedin_username = inputs["linkedin_username"]

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor

        extractor = await get_authenticated_extractor()
        result = await extractor.get_sidebar_profiles(linkedin_username)

        return ToolResult(data=result)
