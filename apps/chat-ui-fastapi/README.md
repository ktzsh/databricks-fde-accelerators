# MyAgent Chatbot - FastAPI + JavaScript (External Auth)

A modern chatbot application with a MyAgent-inspired UI built with FastAPI backend and vanilla JavaScript frontend. **Now configured for external authentication.**

## Features

- 🎨 **Exact MyAgent UI replica** - Modern, flat design matching the MyAgent interface
- 💬 **Chat Management** - Create new chats, browse chat history
- 📁 **File Uploads** - Support for text and image files
- 🔐 **External Authentication** - Works with any external auth system via headers
- 📱 **Responsive Design** - Works on desktop and mobile
- 🗄️ **Persistent Storage** - SQLite database for chat history
- 🚀 **FastAPI Backend** - Modern Python web framework

## External Authentication

This application has been modified to work with **external authentication**. It expects user information to be provided via HTTP headers:

- `X-User-ID`: External user identifier
- `X-User-Email`: User's email address  
- `X-User-Name`: User's display name

See `EXTERNAL_AUTH_MIGRATION.md` for detailed migration information.

## Project Structure

```
chatbot-fastapi-ui/
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI application entry point
│   ├── models.py            # SQLAlchemy database models
│   ├── schemas.py           # Pydantic schemas
│   ├── database.py          # Database configuration
│   ├── utils.py             # User extraction from headers
│   └── routes/
│       ├── __init__.py
│       ├── chats.py         # Chat management routes
│       └── messages.py      # Message handling routes
├── static/
│   ├── index.html           # Main frontend HTML
│   ├── styles.css           # Styling (exact MyAgent replica)
│   └── script.js            # JavaScript frontend logic
├── uploads/                 # File upload directory
├── requirements.txt         # Python dependencies
├── setup.sh                # Setup script
├── run.sh                  # Run script
└── EXTERNAL_AUTH_MIGRATION.md  # Migration guide
```

## Setup Instructions

### 1. Clone or Navigate to the Project
```bash
cd /Users/kshitiz.sharma/Workspace/chatbot-fastapi-ui
```

### 2. Run the Setup Script
```bash
chmod +x setup.sh
./setup.sh
```

### 3. Start the Application
```bash
chmod +x run.sh
./run.sh
```

The application will be available at: http://localhost:8000

**Note:** You'll need to set up your external authentication system to provide the required headers.

## Manual Setup (Alternative)

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create uploads directory
mkdir -p uploads

# Start the server
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## API Endpoints

### User Info
- `GET /user-info` - Get current user info from headers (for debugging)

### Chats
- `POST /api/chats/` - Create new chat
- `GET /api/chats/` - Get user's chat history
- `GET /api/chats/{chat_id}` - Get specific chat with messages
- `PUT /api/chats/{chat_id}` - Update chat title
- `DELETE /api/chats/{chat_id}` - Delete chat

### Messages
- `POST /api/messages/` - Send new message with optional file attachments
- `GET /api/messages/chat/{chat_id}` - Get chat messages
- `POST /api/messages/assistant-response` - Generate assistant response

## Frontend Features

### Exact MyAgent UI Components
- **Sidebar Navigation** - Chat history and new chat creation
- **Welcome Screen** - Suggestion buttons and search input
- **Chat Interface** - Message bubbles with user/assistant styling
- **File Upload Modal** - Drag and drop file support

### Interactive Elements
- Real-time chat messaging
- File attachment support (images and text files)
- Auto-expanding text input
- Typing indicators
- Responsive mobile design

## Database Schema

### Chats Table  
- id, title, user_id (string), user_email, user_name, created_at, updated_at

### Messages Table
- id, chat_id, content, role (user/assistant), created_at

### Message Attachments Table
- id, message_id, filename, file_path, file_type, created_at

## External Auth Integration

### Required Headers
All API requests must include:
```
X-User-ID: user123
X-User-Email: user@example.com
X-User-Name: John Doe
```

### Example Integration
```bash
# Example curl request
curl -X GET "http://localhost:8000/api/chats"  
  -H "X-User-ID: user123"  
  -H "X-User-Email: user@example.com"  
  -H "X-User-Name: John Doe"
```

### Nginx Proxy Example
```nginx
location /api/ {
    auth_request /auth;
    auth_request_set $user_id $upstream_http_x_user_id;
    auth_request_set $user_email $upstream_http_x_user_email;
    auth_request_set $user_name $upstream_http_x_user_name;
    
    proxy_set_header X-User-ID $user_id;
    proxy_set_header X-User-Email $user_email;
    proxy_set_header X-User-Name $user_name;
    
    proxy_pass http://fastapi-backend;
}
```

## Technologies Used

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - SQL toolkit and ORM
- **Pydantic** - Data validation using Python type annotations
- **aiofiles** - Async file operations

### Frontend
- **Vanilla JavaScript** - No frameworks for simplicity
- **Modern CSS** - Flexbox, Grid, CSS variables
- **Inter Font** - Clean, modern typography
- **SVG Icons** - Scalable vector graphics

## Testing with Headers

### Development Testing
For local testing, you can use a simple proxy or modify your requests to include the headers:

```python
# Test script example
import requests

headers = {
    'X-User-ID': 'test-user-123',
    'X-User-Email': 'test@example.com',
    'X-User-Name': 'Test User'
}

response = requests.get('http://localhost:8000/api/chats', headers=headers)
print(response.json())
```

## Production Deployment

### Environment Variables
```
DATABASE_URL=postgresql://user:password@localhost/dbname
DATABRICKS_API_KEY=your-databricks-api-key-here
AGENT_NAME=MyAgent
```

### Docker Deployment
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## Migration from Internal Auth

See `EXTERNAL_AUTH_MIGRATION.md` for complete migration instructions if upgrading from the previous version with internal authentication.

## Contributing

1. Follow the existing code structure
2. Add type hints to Python functions
3. Keep CSS organized and commented
4. Test authentication flows with proper headers
5. Ensure responsive design works

## License

This project is open source and available under the MIT License.
