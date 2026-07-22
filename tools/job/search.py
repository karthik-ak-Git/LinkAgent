"""Search jobs tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier, ToolStability


class SearchJobs(BaseTool):
    name = "search_jobs"
    capability = "job"
    tier = ToolTier.SEARCH
    stability = ToolStability.PRODUCTION
    best_for = ["Searching LinkedIn job postings with filters"]
    input_schema = {
        "type": "object",
        "properties": {
            "keywords": {"type": "string", "description": "Search keywords"},
            "location": {"type": "string", "description": "Location filter"},
            "max_pages": {
                "type": "integer",
                "description": "Max result pages (1-10)",
                "default": 3,
            },
            "date_posted": {
                "type": "string",
                "enum": ["past_hour", "past_24_hours", "past_week", "past_month"],
            },
            "job_type": {
                "type": "string",
                "description": "Comma-separated: full_time, part_time, contract, temporary, volunteer, internship, other",
            },
            "experience_level": {
                "type": "string",
                "description": "Comma-separated: internship, entry, associate, mid_senior, director, executive",
            },
            "work_type": {
                "type": "string",
                "description": "Comma-separated: on_site, remote, hybrid",
            },
            "easy_apply": {"type": "boolean", "description": "Easy Apply only"},
            "sort_by": {
                "type": "string",
                "enum": ["date", "relevance"],
            },
        },
        "required": ["keywords"],
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        keywords = inputs["keywords"]
        location = inputs.get("location")
        max_pages = inputs.get("max_pages", 3)
        date_posted = inputs.get("date_posted")
        job_type = inputs.get("job_type")
        experience_level = inputs.get("experience_level")
        work_type = inputs.get("work_type")
        easy_apply = inputs.get("easy_apply", False)
        sort_by = inputs.get("sort_by")

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor

        extractor = await get_authenticated_extractor()
        result = await extractor.search_jobs(
            keywords,
            location=location,
            max_pages=max_pages,
            date_posted=date_posted,
            job_type=job_type,
            experience_level=experience_level,
            work_type=work_type,
            easy_apply=easy_apply,
            sort_by=sort_by,
        )

        return ToolResult(data=result)
