"""Send message tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier


class SendMessage(BaseTool):
    name = "send_message"
    capability = "messaging"
    tier = ToolTier.ACTIONS
    best_for = ["Sending a LinkedIn message to a user"]
    input_schema = {
        "type": "object",
        "properties": {
            "linkedin_username": {
                "type": "string",
                "description": "LinkedIn username of the recipient",
            },
            "message": {
                "type": "string",
                "description": "Message text to send",
            },
            "confirm_send": {
                "type": "boolean",
                "description": "Must be True to actually send",
            },
            "profile_urn": {
                "type": "string",
                "description": "Optional profile URN for reliable compose URL construction",
            },
        },
        "required": ["linkedin_username", "message", "confirm_send"],
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        linkedin_username = inputs["linkedin_username"]
        message = inputs["message"]
        confirm_send = inputs["confirm_send"]
        profile_urn = inputs.get("profile_urn")

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor

        extractor = await get_authenticated_extractor()
        result = await extractor.send_message(
            linkedin_username,
            message,
            confirm_send=confirm_send,
            profile_urn=profile_urn,
        )

        return ToolResult(data=result)
