"""
Universal data models for extraction results.
"""

from dataclasses import dataclass, field


@dataclass
class ExtractionResult:
    """Generic wrapper for any extraction result."""
    url: str = ""
    title: str = ""
    site: str = ""
    data: dict = field(default_factory=dict)
    error: str = ""


# ── LinkedIn-specific models (kept for backward compatibility) ──

@dataclass
class Post:
    author: str = ""
    headline: str = ""
    text: str = ""
    time: str = ""
    link: str = ""
    likes: str = ""
    comments: str = ""
    reposts: str = ""


@dataclass
class Profile:
    name: str = ""
    headline: str = ""
    location: str = ""
    about: str = ""
    connections: str = ""
    profile_url: str = ""
    experience: list[dict] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    skills: list[str] = field(default_factory=list)
    raw_sections: dict = field(default_factory=dict)


@dataclass
class Company:
    name: str = ""
    headline: str = ""
    about: str = ""
    website: str = ""
    industry: str = ""
    size: str = ""
    headquarters: str = ""
    founded: str = ""
    company_url: str = ""
    employees: list[dict] = field(default_factory=list)
    posts: list[dict] = field(default_factory=list)


@dataclass
class Job:
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    posted: str = ""
    applicants: str = ""
    employment_type: str = ""
    seniority_level: str = ""
    job_url: str = ""
    easy_apply: bool = False


@dataclass
class SearchResult:
    name: str = ""
    headline: str = ""
    location: str = ""
    url: str = ""
    snippet: str = ""
    result_type: str = ""
