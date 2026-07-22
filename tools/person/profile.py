"""Get person profile tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier, ToolStability


class GetPersonProfile(BaseTool):
    name = "get_person_profile"
    capability = "person"
    tier = ToolTier.SCRAPING
    stability = ToolStability.PRODUCTION
    best_for = ["Retrieving a LinkedIn member's profile data by username"]
    not_good_for = ["Your own profile — use get_my_profile"]
    input_schema = {
        "type": "object",
        "properties": {
            "linkedin_username": {
                "type": "string",
                "description": "LinkedIn username (e.g. 'williamhgates')",
            },
            "sections": {
                "type": "string",
                "description": "Comma-separated extra sections: experience, education, interests, honors, languages, certifications, skills, projects, contact_info, posts",
            },
            "max_scrolls": {
                "type": "integer",
                "description": "Max pagination attempts per section (1-50)",
            },
        },
        "required": ["linkedin_username"],
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        linkedin_username = inputs["linkedin_username"]
        sections = inputs.get("sections")
        max_scrolls = inputs.get("max_scrolls")

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor
        from tools._scraping.fields import parse_person_sections

        extractor = await get_authenticated_extractor()
        requested, unknown = parse_person_sections(sections)

        result = await extractor.scrape_person(
            linkedin_username, requested, max_scrolls=max_scrolls
        )

        if unknown:
            result["unknown_sections"] = unknown

        return ToolResult(data=result)
