from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from contextlib import asynccontextmanager
from mongodb import employees, todos, connect_to_mongo, users, private_messages, private_chat_rooms
from mongodb_models import Employee, Gender, Todo, Priority, Status, User, UserLogin, UserResponse, PrivateMessage, PrivateChatRoom
from datetime import datetime, timedelta
from typing import List, Optional
from chat_manager import manager
from auth import verify_password, get_password_hash, create_access_token, verify_token

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await connect_to_mongo()
    yield

app = FastAPI(lifespan=lifespan)

# Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Serve the main dashboard at root
@app.get("/")
async def read_dashboard():
    return FileResponse("static/index.html")

# Serve login page
@app.get("/login")
async def read_login():
    return FileResponse("static/login.html")

# Serve chat page (protected by authentication in frontend)
@app.get("/chat")
async def read_chat():
    return FileResponse("static/chat.html")

# Get all employees
@app.get('/employees')
async def get_all_employees():
    employees_list = await employees.find({}).to_list()

    if not employees_list:
        return {"message" : "No data found."}
    
    # Remove MongoDB's internal _id field to prevent JSON errors
    for emp in employees_list:
        emp.pop('_id', None)
    
    return {
        "message" : "Employees data retrieved successfully.",
        "count" : len(employees_list),
        "data": employees_list
    }

# Get one employee by name
@app.get('/employees/{name}')
async def get_employee(name: str):
    employee = await employees.find_one({"name": name})
    
    if employee:
        employee.pop('_id', None)
        return {
            "message": "Employee data retrieved successfully.",
            "data": employee
        }
    
    raise HTTPException(status_code=404, detail="Employee not found.")

# Create new employee
@app.post('/employees')
async def create_employee(employee: Employee):
    # Check if employee already exists
    existing = await employees.find_one({"name": employee.name})
    if existing:
        raise HTTPException(status_code=400, detail="Employee already exists.")
    
    # Insert new employee
    await employees.insert_one(employee.model_dump())
    return {
        "message": "Employee created successfully.",
        "data": employee.model_dump()
    }

# Update employee (partial update)
@app.patch('/employees/{name}')
async def update_employee(name: str, employee_data: dict):
    # Check if employee exists
    existing = await employees.find_one({"name": name})
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found.")
    
    # Check if updating name and if new name already exists
    if "name" in employee_data and employee_data["name"] != name:
        name_conflict = await employees.find_one({"name": employee_data["name"]})
        if name_conflict:
            raise HTTPException(status_code=400, detail="Employee with this name already exists.")
    
    # Only update fields that are provided in the payload
    if employee_data:
        await employees.update_one({"name": name}, {"$set": employee_data})
    
    # Return updated employee
    updated_employee = await employees.find_one({"name": employee_data.get("name", name)})
    updated_employee.pop('_id', None)
    
    return {
        "message": "Employee updated successfully.",
        "data": updated_employee
    }

@app.delete('/employees/deleteAll')
async def delete_all():
    result = await employees.delete_many({})
    
    if result.deleted_count == 0:
        return {
            "message": "No employees found to delete.",
            "data": {"deleted_count": 0}
        }
    
    return {
        "message": f"Deleted {result.deleted_count} employees successfully.",
        "data": {"deleted_count": result.deleted_count}
    }

# Delete employee
@app.delete('/employees/{name}')
async def delete_employee(name: str):
    # Check if employee exists
    existing = await employees.find_one({"name": name})
    if not existing:
        raise HTTPException(status_code=404, detail="Employee not found.")
    
    # Delete the employee
    await employees.delete_one({"name": name})
    return {
        "message": "Employee deleted successfully.",
        "data": {"name": name}
    }

# ===== TODO CRUD OPERATIONS =====

# Get all todos
@app.get('/todos')
async def get_all_todos():
    todos_list = await todos.find({}).to_list(length=None)
    
    if not todos_list:
        return {"message": "No todos found.", "data": []}
    
    # Remove MongoDB's internal _id field and convert datetime
    for todo in todos_list:
        todo['id'] = str(todo.pop('_id'))  # Convert ObjectId to string ID
        if 'created_at' in todo and todo['created_at']:
            todo['created_at'] = todo['created_at'].isoformat()
        if 'updated_at' in todo and todo['updated_at']:
            todo['updated_at'] = todo['updated_at'].isoformat()
    
    return {
        "message": "Todos retrieved successfully.",
        "count": len(todos_list),
        "data": todos_list
    }

# Get one todo by ID
@app.get('/todos/{todo_id}')
async def get_todo(todo_id: str):
    from bson import ObjectId
    try:
        obj_id = ObjectId(todo_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid todo ID format.")
    
    todo = await todos.find_one({"_id": obj_id})
    
    if todo:
        todo['id'] = str(todo.pop('_id'))  # Convert ObjectId to string ID
        if 'created_at' in todo and todo['created_at']:
            todo['created_at'] = todo['created_at'].isoformat()
        if 'updated_at' in todo and todo['updated_at']:
            todo['updated_at'] = todo['updated_at'].isoformat()
        return {
            "message": "Todo retrieved successfully.",
            "data": todo
        }
    
    raise HTTPException(status_code=404, detail="Todo not found.")

# Create new todo
@app.post('/todos')
async def create_todo(todo: Todo):
    todo_data = todo.model_dump()
    todo_data['created_at'] = datetime.utcnow()
    todo_data['updated_at'] = datetime.utcnow()
    
    result = await todos.insert_one(todo_data)
    
    # Return the created todo with the generated ID
    created_todo = await todos.find_one({"_id": result.inserted_id})
    created_todo['id'] = str(result.inserted_id)  # Add string ID for frontend
    created_todo.pop('_id', None)  # Remove MongoDB ObjectId
    created_todo['created_at'] = created_todo['created_at'].isoformat()
    created_todo['updated_at'] = created_todo['updated_at'].isoformat()
    
    return {
        "message": "Todo created successfully.",
        "data": created_todo
    }

# Update todo (partial update)
@app.patch('/todos/{todo_id}')
async def update_todo(todo_id: str, todo_data: dict):
    from bson import ObjectId
    try:
        obj_id = ObjectId(todo_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid todo ID format.")
    
    # Check if todo exists
    existing = await todos.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Todo not found.")
    
    # Add updated_at timestamp
    todo_data['updated_at'] = datetime.utcnow()
    
    # Only update fields that are provided
    if todo_data:
        await todos.update_one({"_id": obj_id}, {"$set": todo_data})
    
    # Return updated todo
    updated_todo = await todos.find_one({"_id": obj_id})
    updated_todo['id'] = str(updated_todo.pop('_id'))  # Convert ObjectId to string ID
    if 'created_at' in updated_todo and updated_todo['created_at']:
        updated_todo['created_at'] = updated_todo['created_at'].isoformat()
    if 'updated_at' in updated_todo and updated_todo['updated_at']:
        updated_todo['updated_at'] = updated_todo['updated_at'].isoformat()
    
    return {
        "message": "Todo updated successfully.",
        "data": updated_todo
    }

# Delete todo
@app.delete('/todos/{todo_id}')
async def delete_todo(todo_id: str):
    from bson import ObjectId
    try:
        obj_id = ObjectId(todo_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid todo ID format.")
    
    # Check if todo exists
    existing = await todos.find_one({"_id": obj_id})
    if not existing:
        raise HTTPException(status_code=404, detail="Todo not found.")
    
    # Delete the todo
    await todos.delete_one({"_id": obj_id})
    return {
        "message": "Todo deleted successfully.",
        "data": {"id": todo_id}
    }

# Delete all todos
@app.delete('/todos/deleteAll')
async def delete_all_todos():
    result = await todos.delete_many({})
    
    if result.deleted_count == 0:
        return {
            "message": "No todos found to delete.",
            "data": {"deleted_count": 0}
        }
    
    return {
        "message": f"Deleted {result.deleted_count} todos successfully.",
        "data": {"deleted_count": result.deleted_count}
    }

# ===== AUTHENTICATION ENDPOINTS =====

security = HTTPBearer()

async def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Get current authenticated user from JWT token"""
    token = credentials.credentials
    username = verify_token(token)
    if username is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user = await users.find_one({"username": username})
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    user.pop('_id', None)
    user.pop('password', None)  # Remove password from response
    return user

@app.post("/auth/register")
async def register(user: User):
    """Register a new user"""
    # Check if user already exists
    existing_user = await users.find_one({"username": user.username})
    if existing_user:
        raise HTTPException(status_code=400, detail="Username already exists")
    
    existing_email = await users.find_one({"email": user.email})
    if existing_email:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    # Hash password
    hashed_password = get_password_hash(user.password)
    
    # Create user document
    user_doc = {
        "username": user.username,
        "email": user.email,
        "password": hashed_password,
        "display_name": user.display_name,
        "is_active": user.is_active
    }
    
    # Insert user
    await users.insert_one(user_doc)
    
    # Return success response
    return {
        "message": "User registered successfully",
        "username": user.username,
        "email": user.email,
        "display_name": user.display_name
    }

@app.post("/auth/login")
async def login(user_credentials: UserLogin):
    """Login user and return JWT token"""
    # Find user
    user = await users.find_one({"username": user_credentials.username})
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Verify password
    if not verify_password(user_credentials.password, user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    
    # Create access token
    access_token_expires = timedelta(minutes=30)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    
    # Remove password from user data
    user.pop('_id', None)
    user.pop('password', None)
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user
    }

@app.get("/auth/me")
async def get_current_user_info(current_user: dict = Depends(get_current_user)):
    """Get current authenticated user info"""
    return current_user

# ===== PRIVATE MESSAGING ENDPOINTS =====

@app.get("/users/online")
async def get_online_users():
    """Get list of online users"""
    online_users = []
    for websocket, username in manager.users.items():
        if username not in [user["username"] for user in online_users]:
            online_users.append({"username": username})
    return {"users": online_users}

@app.get("/messages/private/{username}")
async def get_private_messages(username: str, current_user: dict = Depends(get_current_user)):
    """Get private messages between current user and specified user"""
    current_username = current_user["username"]
    
    # Get messages between the two users
    messages = await private_messages.find({
        "$or": [
            {"sender": current_username, "receiver": username},
            {"sender": username, "receiver": current_username}
        ]
    }).sort("timestamp", 1).to_list(100)
    
    # Convert ObjectId to string and format timestamps
    for msg in messages:
        msg["_id"] = str(msg["_id"])
        msg["timestamp"] = msg["timestamp"].isoformat()
    
    return {"messages": messages}

@app.post("/messages/private")
async def send_private_message(message: PrivateMessage, current_user: dict = Depends(get_current_user)):
    """Send a private message"""
    # Verify sender is current user
    if message.sender != current_user["username"]:
        raise HTTPException(status_code=403, detail="Cannot send message as another user")

    # Push to ALL active sockets for the receiver first (instant UX), then persist
    payload = {
        "type": "private_message",
        "sender": message.sender,
        "receiver": message.receiver,
        "message": message.message,
        "timestamp": message.timestamp.isoformat()
    }

    recipients = [ws for ws, username in manager.users.items() if username == message.receiver]
    for ws in recipients:
        try:
            await ws.send_json(payload)
        except Exception:
            # Ignore socket errors; proceed to persist
            pass

    # Save message to database (do not block realtime UX)
    message_doc = message.model_dump()
    await private_messages.insert_one(message_doc)

    return {"message": "Private message sent successfully"}

@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    username = None
    try:
        # Wait for join message
        data = await websocket.receive_json()
        if data.get("type") == "join":
            username = data.get("user", f"User_{len(manager.active_connections)}")
            await manager.connect(websocket, username)
        
        while True:
            data = await websocket.receive_json()
            
            if data.get("type") == "message":
                # Broadcast first for snappy UX
                await manager.broadcast({
                    "type": "message",
                    "user": username,
                    "message": data.get("message", ""),
                    "timestamp": datetime.utcnow().isoformat()
                })
                # Persist after
                await manager.save_message(username, data.get("message", ""))
            elif data.get("type") == "private_message":
                # Pure WebSocket private message flow
                receiver = data.get("receiver")
                message_content = data.get("message", "")
                if receiver:
                    # Push to all active sockets of the receiver first (instant UX)
                    payload = {
                        "type": "private_message",
                        "sender": username,
                        "receiver": receiver,
                        "message": message_content,
                        "timestamp": datetime.utcnow().isoformat()
                    }
                    recipients = [ws for ws, user in manager.users.items() if user == receiver]
                    for ws in recipients:
                        try:
                            await ws.send_json(payload)
                        except Exception:
                            pass  # Ignore socket errors; proceed to persist
                    # Persist to database
                    from mongodb_models import PrivateMessage
                    msg = PrivateMessage(
                        sender=username,
                        receiver=receiver,
                        message=message_content,
                        timestamp=datetime.utcnow()
                    )
                    await private_messages.insert_one(msg.model_dump())
            elif data.get("type") == "typing":
                await manager.broadcast({
                    "type": "typing",
                    "user": username
                })
                
    except WebSocketDisconnect:
        if username:
            left_user = manager.disconnect(websocket)
            await manager.broadcast({
                "type": "system",
                "message": f"{left_user} left the chat"
            })
            await manager.broadcast({
                "type": "user_count",
                "count": len(set(manager.users.values()))
            })
            # Also broadcast updated online users list
            await manager.broadcast_online_users()

# Chat page route
@app.get("/chat")
async def read_chat():
    return FileResponse("static/chat.html")

