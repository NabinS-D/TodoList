from fastapi import WebSocket
from typing import List, Dict
from mongodb import chat_messages, private_messages, users
from datetime import datetime, timezone

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
        self.users: dict = {}  # websocket -> username
        self.user_rooms: dict = {}  # username -> list of private rooms

    async def connect(self, websocket: WebSocket, username: str):
        self.active_connections.append(websocket)
        self.users[websocket] = username
        self.user_rooms[username] = []
        
        # Broadcast user count
        await self.broadcast({
            "type": "user_count",
            "count": len(set(self.users.values()))
        })
        
        # Broadcast join message to others (not to the newly connected user)
        await self.broadcast_except({
            "type": "system",
            "message": f"{username} joined the chat"
        }, exclude=websocket)
        
        # Send online users list to all
        await self.broadcast_online_users()

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            username = self.users.pop(websocket, "Unknown")
            
            # Clean up user rooms
            if username in self.user_rooms:
                del self.user_rooms[username]
            
            return username

    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                # Connection was closed, remove it
                if connection in self.active_connections:
                    self.active_connections.remove(connection)
                if connection in self.users:
                    del self.users[connection]

    async def broadcast_except(self, message: dict, exclude: WebSocket):
        """Broadcast a message to all connections except one"""
        for connection in list(self.active_connections):
            if connection is exclude:
                continue
            try:
                await connection.send_json(message)
            except:
                if connection in self.active_connections:
                    self.active_connections.remove(connection)
                if connection in self.users:
                    del self.users[connection]

    async def broadcast_online_users(self):
        """Broadcast updated online users list"""
        online_usernames = list(set(self.users.values()))
        try:
            # Fetch display names for online users
            user_docs = await users.find({
                "username": {"$in": online_usernames}
            }).to_list(len(online_usernames) or 1)

            online_users = [
                {
                    "username": doc.get("username"),
                    "display_name": doc.get("display_name") or doc.get("username")
                }
                for doc in user_docs
            ]

            # Fallback in case collection is empty
            if not online_users:
                online_users = [
                    {"username": u, "display_name": u} for u in online_usernames
                ]
        except Exception:
            # If DB lookup fails, fall back to usernames only
            online_users = [
                {"username": u, "display_name": u} for u in online_usernames
            ]

        await self.broadcast({
            "type": "online_users",
            "users": online_users
        })

    async def send_private_message(self, sender: str, receiver: str, message: str):
        """Send private message to specific user"""
        recipient_websocket = None
        for ws, username in self.users.items():
            if username == receiver:
                recipient_websocket = ws
                break
        
        if recipient_websocket:
            try:
                await recipient_websocket.send_json({
                    "type": "private_message",
                    "sender": sender,
                    "receiver": receiver,
                    "message": message,
                    "timestamp": datetime.utcnow().isoformat()
                })
                return True
            except:
                # Recipient might have disconnected
                return False
        return False

    async def save_message(self, user: str, message: str, room: str = "general"):
        """Save chat message to database"""
        message_doc = {
            "user": user,
            "message": message,
            "timestamp": datetime.now(timezone.utc),
            "room": room
        }
        await chat_messages.insert_one(message_doc)

    async def save_private_message(self, sender: str, receiver: str, message: str):
        """Save private message to database"""
        message_doc = {
            "sender": sender,
            "receiver": receiver,
            "message": message,
            "timestamp": datetime.now(timezone.utc),
            "is_read": False
        }
        await private_messages.insert_one(message_doc)

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

    async def get_private_chat_history(self, user1: str, user2: str, limit: int = 50):
        """Retrieve private chat history between two users"""
        history = await private_messages.find({
            "$or": [
                {"sender": user1, "receiver": user2},
                {"sender": user2, "receiver": user1}
            ]
        }).sort("timestamp", 1).to_list(limit)
        
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
