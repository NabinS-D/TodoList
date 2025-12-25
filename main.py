from fastapi import FastAPI, HTTPException
from contextlib import asynccontextmanager
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from mongodb import employees, todos, connect_to_mongo
from mongodb_models import Employee, Gender, Todo, Priority, Status
from datetime import datetime

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

