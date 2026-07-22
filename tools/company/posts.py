"""Get company posts tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier


class GetCompanyPosts(BaseTool):
    name = "get_company_posts"
    capability = "company"
    tier = ToolTier.SCRAPING
    best_for = ["Getting recent posts from a company's LinkedIn feed"]
    input_schema = {
        "type": "object",
        "properties": {
            "company_name": {
                "type": "string",
                "description": "LinkedIn company slug (e.g. 'docker', 'anthropic')",
            },
        },
        "required": ["company_name"],
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        company_name = inputs["company_name"]

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor

        extractor = await get_authenticated_extractor()
        url = f"https://www.linkedin.com/company/{company_name}/posts/"
        extracted = await extractor.extract_page(url, section_name="posts")

        sections = {}
        references = {}
        section_errors = {}

        if extracted.text:
            sections["posts"] = extracted.text
            if extracted.references:
                references["posts"] = extracted.references
        elif extracted.error:
            section_errors["posts"] = extracted.error

        data = {"url": url, "sections": sections}
        if references:
            data["references"] = references
        if section_errors:
            data["section_errors"] = section_errors

        return ToolResult(data=data)
