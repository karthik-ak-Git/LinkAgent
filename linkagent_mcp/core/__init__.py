"""
Core extraction framework.

Provides the base classes and infrastructure for building site extractors:

- BaseExtractor: Abstract base class for all extractors
- Registry: Central registry mapping tool names to extractor classes
- ExtractionResult: Standardized output model
"""

from .base import BaseExtractor
from .registry import Registry, registry
from .models import ExtractionResult

__all__ = ["BaseExtractor", "Registry", "registry", "ExtractionResult"]
