"""Private infrastructure: extraction engine and field configs.

Bridges to linkedin-mcp-server's scraping package.
Will be refactored into standalone modules.
"""

from __future__ import annotations

import sys as _sys

from tools._scraping.fields import (
    COMPANY_SECTIONS,
    PERSON_SECTIONS,
    parse_company_sections,
    parse_person_sections,
)

__all__ = [
    "COMPANY_SECTIONS",
    "LinkedInExtractor",
    "PERSON_SECTIONS",
    "parse_company_sections",
    "parse_person_sections",
]


def __getattr__(name: str):
    if name == "LinkedInExtractor":
        from linkedin_mcp_server.scraping import LinkedInExtractor as _extractor

        _sys.modules[__name__].LinkedInExtractor = _extractor
        return _extractor
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
