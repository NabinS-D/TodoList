# FastAPI TodoList & Employee Management App

A comprehensive FastAPI application with dual functionality: Employee Management and TodoList tracking, built with MongoDB for data persistence and a modern web interface.

## Setup Instructions

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. MongoDB Setup
Make sure you have MongoDB server running and create a database:

```bash
# Start MongoDB (if using local installation)
mongod

# Or connect to MongoDB Atlas (cloud)
# Update connection string in mongodb.py
```

### 3. Configure Database Connection
Update the MongoDB connection in `mongodb.py`:

```python
MONGO_URI = "mongodb://localhost:27017/fastapi_db"
# or for MongoDB Atlas
# MONGO_URI = "mongodb+srv://username:password@cluster.mongodb.net/fastapi_db"
```

**Note:** Configuration files are excluded from git by `.gitignore` to protect sensitive credentials.

### 4. Initialize Database
Run the initialization script to create collections and seed sample data:

```bash
python init_db.py
```

**Note:** The app automatically creates collections on first use if they don't exist.

### 5. Run the Application
```bash
uvicorn main:app --reload
```

## Features

### Employee Management
- **GET** `/employees` - Retrieve all employees
- **GET** `/employees/{name}` - Get employee by name
- **POST** `/employees` - Create new employee
- **PATCH** `/employees/{name}` - Update employee details
- **DELETE** `/employees/{name}` - Delete specific employee
- **DELETE** `/employees/deleteAll` - Delete all employees

### TodoList Management
- **GET** `/todos` - Retrieve all todos
- **GET** `/todos/{todo_id}` - Get specific todo
- **POST** `/todos` - Create new todo
- **PATCH** `/todos/{todo_id}` - Update todo (status, priority, etc.)
- **DELETE** `/todos/{todo_id}` - Delete specific todo
- **DELETE** `/todos/deleteAll` - Delete all todos

### Web Interface
- **GET** `/` - Main dashboard with employee and todo management UI
- **Static Files** `/static/*` - Served frontend assets

## Data Models

### Employee Schema
- `name` (String) - Employee name
- `surname` (String) - Employee surname
- `age` (Integer) - Employee age
- `gender` (Enum: male, female, other)

### Todo Schema
- `title` (String) - Todo title
- `description` (String) - Detailed description
- `status` (Enum: pending, in_progress, completed)
- `priority` (Enum: low, medium, high)
- `created_at` (DateTime) - Auto-generated timestamp
- `updated_at` (DateTime) - Auto-updated on changes

## Files Added/Modified

- `main.py` - FastAPI application with employee and todo CRUD operations
- `mongodb.py` - MongoDB connection and collection setup
- `mongodb_models.py` - Pydantic models for data validation
- `.gitignore` - Git ignore file to exclude sensitive data and cache files
- `requirements.txt` - Python dependencies including FastAPI and MongoDB drivers
- `static/index.html` - Frontend dashboard for managing employees and todos
- `README.md` - Updated documentation
