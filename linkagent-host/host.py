#!/usr/bin/env python3
"""
LinkAgent Native Messaging Host

Bridges Chrome extension (native messaging) to the MCP server.
Reads length-prefixed JSON from stdin, forwards to MCP server via WebSocket.
Handles keep-alive to maintain stable connection.
"""

import json
import struct
import sys
import asyncio
import signal
from websockets.client import connect

# Native messaging uses 4-byte length prefix + JSON
MCP_WS_URL = "ws://localhost:8765"

# Keep track of WebSocket connection
ws_connection = None


def read_message():
    """Read a length-prefixed JSON message from stdin."""
    try:
        raw_length = sys.stdin.buffer.read(4)
        if not raw_length or len(raw_length) < 4:
            return None
        length = struct.unpack('=I', raw_length)[0]
        if length > 10 * 1024 * 1024:  # 10MB max
            return None
        data = sys.stdin.buffer.read(length)
        if len(data) < length:
            return None
        return json.loads(data.decode('utf-8'))
    except Exception as e:
        print(f"[Host] Read error: {e}", file=sys.stderr)
        return None


def send_message(msg):
    """Send a length-prefixed JSON message to stdout."""
    try:
        encoded = json.dumps(msg).encode('utf-8')
        sys.stdout.buffer.write(struct.pack('=I', len(encoded)))
        sys.stdout.buffer.write(encoded)
        sys.stdout.buffer.flush()
    except Exception as e:
        print(f"[Host] Write error: {e}", file=sys.stderr)


async def get_ws_connection():
    """Get or create WebSocket connection to MCP server."""
    global ws_connection

    if ws_connection and ws_connection.open:
        return ws_connection

    try:
        ws_connection = await connect(
            MCP_WS_URL,
            ping_interval=20,
            ping_timeout=10,
            close_timeout=5,
        )
        print("[Host] Connected to MCP server", file=sys.stderr)
        return ws_connection
    except Exception as e:
        print(f"[Host] WebSocket connection failed: {e}", file=sys.stderr)
        ws_connection = None
        return None


async def forward_to_mcp(message):
    """Forward a message to the MCP server via WebSocket."""
    ws = await get_ws_connection()
    if not ws:
        return {"error": "WebSocket connection failed"}

    try:
        await ws.send(json.dumps(message))
        response = await asyncio.wait_for(ws.recv(), timeout=30.0)
        return json.loads(response)
    except asyncio.TimeoutError:
        return {"error": "MCP server timeout"}
    except Exception as e:
        print(f"[Host] Forward error: {e}", file=sys.stderr)
        # Try to reconnect on next call
        global ws_connection
        ws_connection = None
        return {"error": str(e)}


def handle_keep_alive(message):
    """Handle keep-alive messages from the extension."""
    if message.get('method') in ('keepAlive', 'ping'):
        send_message({"method": "pong"})
        return True
    return False


async def main():
    """Main loop: read from Chrome extension, forward to MCP server."""
    print("[Host] Starting native messaging host...", file=sys.stderr)

    while True:
        message = read_message()
        if message is None:
            print("[Host] stdin closed, exiting", file=sys.stderr)
            break

        # Handle keep-alive locally (don't forward to MCP)
        if handle_keep_alive(message):
            continue

        # Log command
        cmd = message.get('command') or message.get('method', 'unknown')
        print(f"[Host] Received: {cmd}", file=sys.stderr)

        # Forward to MCP server
        response = await forward_to_mcp(message)

        # Send response back to Chrome extension
        send_message(response)


if __name__ == '__main__':
    # Handle signals gracefully (SIGPIPE not available on Windows)
    if hasattr(signal, 'SIGPIPE'):
        signal.signal(signal.SIGPIPE, signal.SIG_DFL)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n[Host] Shutting down...", file=sys.stderr)
    except Exception as e:
        print(f"[Host] Fatal error: {e}", file=sys.stderr)
        sys.exit(1)
