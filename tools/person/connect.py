"""Connect with person tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier, ToolStability


class ConnectWithPerson(BaseTool):
    name = "connect_with_person"
    capability = "person"
    tier = ToolTier.ACTIONS
    stability = ToolStability.PRODUCTION
    best_for = ["Sending LinkedIn connection requests with optional notes"]
    not_good_for = ["Messaging — use send_message"]
    input_schema = {
        "type": "object",
        "properties": {
            "linkedin_username": {
                "type": "string",
                "description": "LinkedIn username to connect with",
            },
            "note": {
                "type": "string",
                "description": "Optional personalized invitation note",
            },
        },
        "required": ["linkedin_username"],
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        linkedin_username = inputs["linkedin_username"]
        note = inputs.get("note")

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor

        extractor = await get_authenticated_extractor()
        result = await extractor.connect_with_person(linkedin_username, note=note)

        return ToolResult(data=result)
