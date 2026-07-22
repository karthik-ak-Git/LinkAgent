"""Get company employees tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier


class GetCompanyEmployees(BaseTool):
    name = "get_company_employees"
    capability = "company"
    tier = ToolTier.SCRAPING
    best_for = ["Listing employees at a company with location, education, and function breakdown"]
    input_schema = {
        "type": "object",
        "properties": {
            "company_name": {
                "type": "string",
                "description": "LinkedIn company URL slug (e.g. 'docker', 'anthropicresearch')",
            },
            "keywords": {
                "type": "string",
                "description": "Optional filter by name, title, or skill",
            },
        },
        "required": ["company_name"],
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        company_name = inputs["company_name"]
        keywords = inputs.get("keywords")

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor

        extractor = await get_authenticated_extractor()
        result = await extractor.get_company_employees(company_name, keywords=keywords)

        return ToolResult(data=result)
