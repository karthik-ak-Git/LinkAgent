"""Search people tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier, ToolStability


class SearchPeople(BaseTool):
    name = "search_people"
    capability = "person"
    tier = ToolTier.SEARCH
    stability = ToolStability.PRODUCTION
    best_for = ["Finding LinkedIn members by keyword, location, company, or network degree"]
    input_schema = {
        "type": "object",
        "properties": {
            "keywords": {"type": "string", "description": "Search keywords"},
            "location": {"type": "string", "description": "Location filter (e.g. 'New York')"},
            "network": {
                "type": "array",
                "items": {"type": "string", "enum": ["F", "S", "O"]},
                "description": "Connection-degree filter: F=1st, S=2nd, O=3rd+",
            },
            "current_company": {
                "type": "string",
                "description": "Current-employer filter (use numeric URN id for reliability)",
            },
        },
        "required": ["keywords"],
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        keywords = inputs["keywords"]
        location = inputs.get("location")
        network = inputs.get("network")
        current_company = inputs.get("current_company")

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor

        extractor = await get_authenticated_extractor()
        result = await extractor.search_people(
            keywords,
            location,
            network=network,
            current_company=current_company,
        )

        return ToolResult(data=result)
