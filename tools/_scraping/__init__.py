"""Private infrastructure: extraction engine and field configs.

Bridges to linkedin-mcp-server's scraping package.
Will be refactored into standalone modules.
"""

from __future__ import annotations

from tools._scraping.fields import (
    COMPANY_SECTIONS,
    PERSON_SECTIONS,
    parse_company_sections,
    parse_person_sections,
)
from linkedin_mcp_server.scraping import LinkedInExtractor

__all__ = [
    "COMPANY_SECTIONS",
    "LinkedInExtractor",
    "PERSON_SECTIONS",
    "parse_company_sections",
    "parse_person_sections",
]
