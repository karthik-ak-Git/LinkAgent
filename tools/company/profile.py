"""Get company profile tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier, ToolStability


class GetCompanyProfile(BaseTool):
    name = "get_company_profile"
    capability = "company"
    tier = ToolTier.SCRAPING
    stability = ToolStability.PRODUCTION
    best_for = ["Retrieving a LinkedIn company's about page, posts, and jobs"]
    input_schema = {
        "type": "object",
        "properties": {
            "company_name": {
                "type": "string",
                "description": "LinkedIn company slug (e.g. 'docker', 'anthropic', 'microsoft')",
            },
            "sections": {
                "type": "string",
                "description": "Comma-separated extra sections: posts, jobs",
            },
        },
        "required": ["company_name"],
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        company_name = inputs["company_name"]
        sections = inputs.get("sections")

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor
        from tools._scraping.fields import parse_company_sections

        extractor = await get_authenticated_extractor()
        requested, unknown = parse_company_sections(sections)

        result = await extractor.scrape_company(company_name, requested)

        if unknown:
            result["unknown_sections"] = unknown

        return ToolResult(data=result)
