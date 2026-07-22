"""Get my profile tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier, ToolStability


class GetMyProfile(BaseTool):
    name = "get_my_profile"
    capability = "person"
    tier = ToolTier.SCRAPING
    stability = ToolStability.PRODUCTION
    best_for = ["Retrieving the authenticated user's own LinkedIn profile"]
    input_schema = {
        "type": "object",
        "properties": {
            "sections": {
                "type": "string",
                "description": "Comma-separated extra sections: experience, education, interests, honors, languages, certifications, skills, projects, contact_info, posts",
            },
            "max_scrolls": {
                "type": "integer",
                "description": "Max pagination attempts per section (1-50)",
            },
        },
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        sections = inputs.get("sections")
        max_scrolls = inputs.get("max_scrolls")

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor
        from tools._scraping.fields import parse_person_sections
        from tools._browser import get_browser

        extractor = await get_authenticated_extractor()
        requested, unknown = parse_person_sections(sections)

        result = await extractor.get_my_profile(
            sections=requested, max_scrolls=max_scrolls
        )

        if unknown:
            result["unknown_sections"] = unknown

        return ToolResult(data=result)
