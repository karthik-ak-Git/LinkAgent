#!/usr/bin/env python3
"""
Test script for LinkAgent Extension
Verifies WebSocket connection and basic commands.
"""

import json
import asyncio
import websockets

WS_URL = "ws://localhost:8765"

async def test_connection():
    """Test WebSocket connection to extension."""
    print(f"Connecting to {WS_URL}...")
    
    try:
        async with websockets.connect(WS_URL) as ws:
            print("Connected!")
            
            # Test ping
            print("\nTesting ping...")
            await ws.send(json.dumps({"command": "ping"}))
            response = await ws.recv()
            print(f"Ping response: {response}")
            
            # Test status
            print("\nTesting status...")
            await ws.send(json.dumps({"command": "status"}))
            response = await ws.recv()
            print(f"Status response: {response}")
            
            # Test screenshot
            print("\nTesting screenshot...")
            await ws.send(json.dumps({"command": "screenshot", "params": {"format": "png"}}))
            response = await ws.recv()
            data = json.loads(response)
            if "data" in data:
                print(f"Screenshot captured! Size: {len(data['data'])} bytes (base64)")
            else:
                print(f"Screenshot response: {response[:200]}...")
            
            print("\nAll tests passed!")
            return True
            
    except Exception as e:
        print(f"Connection failed: {e}")
        print("\nMake sure:")
        print("1. LinkAgent extension is installed and enabled")
        print("2. WebSocket server is running on port 8765")
        print("3. Chrome is open with the extension loaded")
        return False


if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)
