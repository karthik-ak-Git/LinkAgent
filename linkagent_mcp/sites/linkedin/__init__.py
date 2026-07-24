"""
LinkedIn site module — registers all LinkedIn extractors with the registry.

Usage:
    from linkagent_mcp.sites.linkedin import register
    register(registry)
"""

from ...core.registry import Registry


def register(registry: Registry):
    """Register all LinkedIn extractors."""
    from .extractors import (
        FeedExtractor,
        ProfileExtractor,
        CompanyExtractor,
        JobExtractor,
        SearchExtractor,
    )

    registry.register(
        name="linkedin_feed",
        extractor_class=FeedExtractor,
        domain="linkedin.com",
        description="Extract posts from the LinkedIn feed. Returns authors, headlines, post text, links, and engagement metrics.",
        input_schema={"type": "object", "properties": {}},
        navigate_url="https://www.linkedin.com/feed/",
        url_patterns=["/feed"],
    )

    registry.register(
        name="linkedin_profile",
        extractor_class=ProfileExtractor,
        domain="linkedin.com",
        description="Extract a LinkedIn person profile. Provide username or navigate to profile first.",
        input_schema={
            "type": "object",
            "properties": {
                "username": {
                    "type": "string",
                    "description": "LinkedIn username (from URL /in/username)",
                },
            },
        },
        url_patterns=["/in/"],
    )

    registry.register(
        name="linkedin_company",
        extractor_class=CompanyExtractor,
        domain="linkedin.com",
        description="Extract a LinkedIn company page. Provide company name or navigate first.",
        input_schema={
            "type": "object",
            "properties": {
                "company_name": {
                    "type": "string",
                    "description": "LinkedIn company name (from URL /company/name)",
                },
            },
        },
        url_patterns=["/company/"],
    )

    registry.register(
        name="linkedin_jobs",
        extractor_class=JobExtractor,
        domain="linkedin.com",
        description="Search jobs or extract job details. Provide keyword for search, or job_id for detail.",
        input_schema={
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Job search keyword",
                },
                "job_id": {
                    "type": "string",
                    "description": "LinkedIn job ID (from URL /jobs/view/{id})",
                },
            },
        },
        navigate_url="https://www.linkedin.com/jobs/search/",
        url_patterns=["/jobs/"],
    )

    registry.register(
        name="linkedin_search",
        extractor_class=SearchExtractor,
        domain="linkedin.com",
        description="Search for people or companies on LinkedIn.",
        input_schema={
            "type": "object",
            "properties": {
                "keyword": {
                    "type": "string",
                    "description": "Search keyword",
                },
                "search_type": {
                    "type": "string",
                    "enum": ["people", "company"],
                    "default": "people",
                    "description": "Type of search: people or company",
                },
            },
        },
        url_patterns=["/search/results/"],
    )
