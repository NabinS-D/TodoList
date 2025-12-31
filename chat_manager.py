from fastapi import WebSocket
from typing import List
from mongodb import chat_messages
from datetime import datetime, timezone

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.users: dict = {}  # websocket -> username

    async def connect(self, websocket: WebSocket, username: str):
        self.active_connections.append(websocket)
        self.users[websocket] = username
        
        # Broadcast user count
        await self.broadcast({
            "type": "user_count",
            "count": len(self.active_connections)
        })
        
        # Broadcast join message
        await self.broadcast({
            "type": "system",
            "message": f"{username} joined the chat"
        })

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            username = self.users.pop(websocket, "Unknown")
            
            # Broadcast user count and leave message
            return username

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Connection was closed, remove it
                self.active_connections.remove(connection)

    async def save_message(self, user: str, message: str, room: str = "general"):
        """Save chat message to database"""
        message_doc = {
            "user": user,
            "message": message,
            "timestamp": datetime.now(timezone.utc),
            "room": room
        }
        await chat_messages.insert_one(message_doc)

    async def get_chat_history(self, room: str = "general", limit: int = 50):
        """Retrieve recent chat history from database"""
        history = await chat_messages.find(
            {"room": room}
        ).sort("timestamp", 1).to_list(limit)
        
        # Convert ObjectId to string and format timestamps
        for msg in history:
            msg["_id"] = str(msg["_id"])
            msg["timestamp"] = msg["timestamp"].isoformat()
            
        return history

    async def send_chat_history(self, websocket: WebSocket, room: str = "general"):
        """Send chat history to a newly connected user"""
        history = await self.get_chat_history(room)
        for msg in history:
            await websocket.send_json({
                "type": "message",
                "user": msg["user"],
                "message": msg["message"],
                "timestamp": msg["timestamp"]
            })

# Global connection manager instance
manager = ConnectionManager()
