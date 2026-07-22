"""Get job details tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier, ToolStability


class GetJobDetails(BaseTool):
    name = "get_job_details"
    capability = "job"
    tier = ToolTier.SCRAPING
    stability = ToolStability.PRODUCTION
    best_for = ["Retrieving full details of a LinkedIn job posting by its numeric ID"]
    input_schema = {
        "type": "object",
        "properties": {
            "job_id": {
                "type": "string",
                "description": "LinkedIn job ID (e.g. '4252026496')",
            },
        },
        "required": ["job_id"],
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        job_id = inputs["job_id"]

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor

        extractor = await get_authenticated_extractor()
        result = await extractor.scrape_job(job_id)

        return ToolResult(data=result)
