import asyncio
import websockets
import json

async def test_websocket():
    uri = "ws://localhost:8000/ws/chat"
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected to WebSocket server")
            
            # Send a test message
            test_message = {
                "type": "chat",
                "message": "Hello, this is a test message"
            }
            
            await websocket.send(json.dumps(test_message))
            print("Sent test message:", test_message)
            
            # Wait for response
            response = await websocket.recv()
            print("Received response:", response)
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_websocket()) 