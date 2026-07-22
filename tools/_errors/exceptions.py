"""Custom exceptions for LinkedIn scraping operations."""


class LinkedInScraperException(Exception):
    """Base exception for LinkedIn scraper."""


class AuthenticationError(LinkedInScraperException):
    """Raised when authentication fails."""


class RateLimitError(LinkedInScraperException):
    """Raised when rate limiting is detected."""

    def __init__(self, message: str, suggested_wait_time: int = 300):
        super().__init__(message)
        self.suggested_wait_time = suggested_wait_time


class ElementNotFoundError(LinkedInScraperException):
    """Raised when an expected element is not found."""


class ProfileNotFoundError(LinkedInScraperException):
    """Raised when a profile/page returns 404."""


class NetworkError(LinkedInScraperException):
    """Raised when network-related issues occur."""


class ScrapingError(LinkedInScraperException):
    """Raised when scraping fails for various reasons."""
