"""Get feed tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier, ToolStability


class GetFeed(BaseTool):
    name = "get_feed"
    capability = "feed"
    tier = ToolTier.SCRAPING
    stability = ToolStability.PRODUCTION
    best_for = ["Retrieving posts from the authenticated user's LinkedIn home feed"]
    input_schema = {
        "type": "object",
        "properties": {
            "num_posts": {
                "type": "integer",
                "description": "Number of posts to fetch (1-50)",
                "default": 10,
            },
        },
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        num_posts = inputs.get("num_posts", 10)

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor

        extractor = await get_authenticated_extractor()
        extracted = await extractor.extract_feed(num_posts=num_posts)

        url = "https://www.linkedin.com/feed/"
        sections = {}
        references = {}
        section_errors = {}

        if extracted.text:
            sections["feed"] = extracted.text
            if extracted.references:
                references["feed"] = extracted.references
        elif extracted.error:
            section_errors["feed"] = extracted.error

        data = {"url": url, "sections": sections}
        if references:
            data["references"] = references
        if section_errors:
            data["section_errors"] = section_errors

        return ToolResult(data=data)
