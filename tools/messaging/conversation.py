"""Get conversation tool."""

from __future__ import annotations

from typing import Any

from tools.base_tool import BaseTool, ToolResult, ToolTier


class GetConversation(BaseTool):
    name = "get_conversation"
    capability = "messaging"
    tier = ToolTier.SCRAPING
    best_for = ["Reading a specific LinkedIn messaging conversation by participant or thread ID"]
    input_schema = {
        "type": "object",
        "properties": {
            "linkedin_username": {
                "type": "string",
                "description": "LinkedIn username of the conversation participant",
            },
            "thread_id": {
                "type": "string",
                "description": "LinkedIn messaging thread ID",
            },
            "index": {
                "type": "integer",
                "description": "0-based selector when participant has multiple threads",
                "default": 0,
            },
        },
    }

    async def execute(self, inputs: dict[str, Any]) -> ToolResult:
        linkedin_username = inputs.get("linkedin_username")
        thread_id = inputs.get("thread_id")
        index = inputs.get("index", 0)

        if not linkedin_username and not thread_id:
            return ToolResult(
                success=False,
                error="Provide at least one of linkedin_username or thread_id",
            )

        from tools._scraping import LinkedInExtractor
        from tools._auth import get_authenticated_extractor

        extractor = await get_authenticated_extractor()
        result = await extractor.get_conversation(
            linkedin_username=linkedin_username,
            thread_id=thread_id,
            index=index,
        )

        return ToolResult(data=result)
