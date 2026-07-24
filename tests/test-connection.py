#!/usr/bin/env python3
"""
LinkAgent Connection Stability Test

Tests WebSocket connection stability and keeps it alive.
Run this to verify the connection stays stable.
"""

import json
import asyncio
import time
import sys
from websockets.client import connect

WS_URL = "ws://localhost:8765"

async def test_connection_stability():
    """Test that connection stays stable over time."""
    print(f"Connecting to {WS_URL}...")
    print("Press Ctrl+C to stop\n")

    try:
        async with connect(
            WS_URL,
            ping_interval=10,
            ping_timeout=5,
            close_timeout=5,
        ) as ws:
            print("Connected!\n")
            print(f"{'Time':<12} {'Status':<15} {'Details'}")
            print("-" * 50)

            start_time = time.time()

            # Test ping immediately
            await ws.send(json.dumps({"command": "ping", "id": 1}))
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            elapsed = time.time() - start_time
            print(f"{elapsed:>8.1f}s   {'OK':<15} Ping response received")

            # Keep connection alive and monitor
            message_id = 2
            last_message_time = time.time()

            while True:
                try:
                    # Send periodic keep-alive
                    await asyncio.sleep(2)

                    # Check if we received any messages recently
                    elapsed = time.time() - start_time
                    since_last = time.time() - last_message_time

                    # Send a ping
                    await ws.send(json.dumps({
                        "command": "ping",
                        "id": message_id
                    }))
                    message_id += 1

                    # Try to receive with timeout
                    try:
                        response = await asyncio.wait_for(ws.recv(), timeout=3.0)
                        last_message_time = time.time()
                        data = json.loads(response)
                        print(f"{elapsed:>8.1f}s   {'OK':<15} Pong received (id={data.get('id', '?')})")
                    except asyncio.TimeoutError:
                        print(f"{elapsed:>8.1f}s   {'WARNING':<15} No response (timeout)")

                except asyncio.CancelledError:
                    break
                except Exception as e:
                    elapsed = time.time() - start_time
                    print(f"{elapsed:>8.1f}s   {'ERROR':<15} {e}")
                    break

    except Exception as e:
        print(f"Connection failed: {e}")
        print("\nMake sure:")
        print("1. LinkAgent extension is installed in Chrome")
        print("2. Extension is enabled and connected")
        print("3. WebSocket server is running on port 8765")
        return False

    return True


if __name__ == "__main__":
    try:
        asyncio.run(test_connection_stability())
    except KeyboardInterrupt:
        print("\n\nTest stopped by user")
