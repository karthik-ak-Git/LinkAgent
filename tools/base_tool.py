"""Base tool contract for all LinkedIn MCP tools.

Inherited from OpenMontage's BaseTool pattern. Every LinkedIn tool
subclasses this to declare metadata and implement execute(inputs) -> ToolResult.

__init_subclass__ auto-instruments each concrete execute() with
timing and error classification.
"""

from __future__ import annotations

import functools
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Optional


class ToolTier(str, Enum):
    CORE = "core"
    SEARCH = "search"
    ACTIONS = "actions"
    SCRAPING = "scraping"


class ToolStability(str, Enum):
    EXPERIMENTAL = "experimental"
    BETA = "beta"
    PRODUCTION = "production"


class ToolStatus(str, Enum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    DEGRADED = "degraded"


class ToolRuntime(str, Enum):
    LOCAL = "local"
    DOCKER = "docker"
    REMOTE = "remote"


class ExecutionMode(str, Enum):
    SYNC = "sync"
    ASYNC = "async"


class Determinism(str, Enum):
    DETERMINISTIC = "deterministic"
    STOCHASTIC = "stochastic"


@dataclass
class ToolResult:
    success: bool = True
    data: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    duration_seconds: float = 0.0
    meta: dict[str, Any] = field(default_factory=dict)


def _instrument_execute(fn):
    """Wrap execute() with timing — strictly non-fatal."""
    if getattr(fn, "_linkedin_instrumented", False):
        return fn

    @functools.wraps(fn)
    async def wrapper(self, inputs, *args, **kwargs):
        started = time.monotonic()
        try:
            result = await fn(self, inputs, *args, **kwargs)
            result.duration_seconds = round(time.monotonic() - started, 3)
            return result
        except Exception as exc:
            elapsed = round(time.monotonic() - started, 3)
            return ToolResult(
                success=False,
                error=f"{type(exc).__name__}: {exc}",
                duration_seconds=elapsed,
            )

    wrapper._linkedin_instrumented = True
    return wrapper


class BaseTool(ABC):
    """Abstract base class for all LinkedIn MCP tools."""

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        impl = cls.__dict__.get("execute")
        if impl is not None and not getattr(impl, "__isabstractmethod__", False):
            cls.execute = _instrument_execute(impl)

    name: str = ""
    version: str = "0.1.0"
    tier: ToolTier = ToolTier.CORE
    stability: ToolStability = ToolStability.PRODUCTION
    execution_mode: ExecutionMode = ExecutionMode.ASYNC
    determinism: Determinism = Determinism.DETERMINISTIC
    runtime: ToolRuntime = ToolRuntime.LOCAL

    dependencies: list[str] = []
    capability: str = "generic"
    provider: str = "linkedin"
    capabilities: list[str] = []
    input_schema: dict = {}
    best_for: list[str] = []
    not_good_for: list[str] = []
    fallback_tools: list[str] = []

    def get_status(self) -> ToolStatus:
        return ToolStatus.AVAILABLE

    @abstractmethod
    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        ...
