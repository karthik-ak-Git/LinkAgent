"""Core package — universal extraction framework."""

from .base import BaseExtractor
from .registry import Registry, registry
from .models import ExtractionResult

__all__ = ["BaseExtractor", "Registry", "registry", "ExtractionResult"]
