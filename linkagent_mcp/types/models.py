"""
Data models for LinkedIn extraction results.
"""

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Post:
    """A LinkedIn feed post."""
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
    """A LinkedIn person profile."""
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
    """A LinkedIn company page."""
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
    """A LinkedIn job listing."""
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
    """A search result item (person or company)."""
    name: str = ""
    headline: str = ""
    location: str = ""
    url: str = ""
    snippet: str = ""
    result_type: str = ""  # "person" or "company"
