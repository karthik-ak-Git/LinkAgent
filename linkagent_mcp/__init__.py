"""
LinkAgent MCP — Universal browser-based extraction via CDP.

Core:
    core.base       — BaseExtractor (subclass this for new sites)
    core.registry   — Registry (register extractors here)
    core.models     — Data models

Sites:
    sites.linkedin  — LinkedIn extractors (feed, profile, company, jobs, search)

To add a new site:
    1. Create sites/mysite/__init__.py
    2. Implement extractors subclassing core.BaseExtractor
    3. Expose register(registry) function
    4. It's auto-discovered on server start
"""
