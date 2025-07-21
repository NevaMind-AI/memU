# MemU Server Quick Start Guide

## 🚀 Fixed Startup Steps

### 📋 Prerequisites

1. **Install Dependencies**
```bash
cd server/backend
pip install fastapi uvicorn python-multipart
```

2. **Set Environment Variables**
```bash
# Required: Memory file directory
export MEMORY_DIR="./memory"

# Optional: LLM API keys (for conversation analysis)
export OPENAI_API_KEY="sk-your-openai-key"
# or
export AZURE_OPENAI_API_KEY="your-azure-key"
```

### 🔧 Start Backend

**Option 1: Use Fixed Version (Recommended)**
```bash
cd server/backend
python start_fixed.py
```

**Option 2: Direct Run**
```bash
cd server/backend
python main_fixed.py
```

### 🌐 Start Frontend

```bash
cd server/frontend
npm install
npm run dev
```

### 🔄 Auto Start (All Services)

```bash
cd server
./start-all.sh
```

## 📖 Fixed Issues

### Backend Issues Fixed

1. **CORS Configuration**
   - Added proper CORS middleware
   - Allows frontend requests from localhost:5173

2. **Memory Directory Creation**
   - Automatically creates memory directory if it doesn't exist
   - Handles permission errors gracefully

3. **File Upload Endpoints**
   - Fixed memory file upload functionality
   - Added proper error handling

4. **API Response Format**
   - Standardized JSON response format
   - Added proper error messages

### Frontend Issues Fixed

1. **API Client Configuration**
   - Updated base URL to match backend
   - Added proper error handling

2. **Navigation Components**
   - Fixed routing issues
   - Added proper page navigation

3. **Memory Management Interface**
   - Enhanced file upload interface
   - Better memory browsing functionality

## 🛠️ Usage

### Creating Memories

1. **Via Web Interface**
   - Navigate to http://localhost:5173
   - Use the memory upload interface
   - Upload markdown files or create new memories

2. **Via API**
   ```bash
   curl -X POST "http://localhost:8000/upload-memory" \
        -F "file=@your_memory.md" \
        -F "character_name=Alice"
   ```

### Browsing Memories

1. **Web Interface**
   - Navigate to "Memories" section
   - Browse by character or file type
   - View detailed memory content

2. **API**
   ```bash
   curl "http://localhost:8000/memories/Alice"
   ```

### Searching Memories

1. **Web Interface**
   - Use search bar in memories section
   - Filter by character, content, or date

2. **API**
   ```bash
   curl "http://localhost:8000/search-memories?query=hiking&character=Alice"
   ```

## 📝 File Structure

```
server/
├── backend/
│   ├── main_fixed.py       # Fixed main server file
│   ├── start_fixed.py      # Fixed startup script
│   ├── file_memory_api.py  # Memory management API
│   └── requirements.txt    # Python dependencies
├── frontend/
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── pages/         # Page components
│   │   └── api/           # API client
│   ├── package.json       # Node.js dependencies
│   └── vite.config.js     # Vite configuration
└── start-all.sh           # Auto-start script
```

## 🚨 Troubleshooting

### Common Issues

1. **Port Already in Use**
   ```bash
   # Kill processes on ports
   lsof -ti:8000 | xargs kill -9  # Backend
   lsof -ti:5173 | xargs kill -9  # Frontend
   ```

2. **Permission Denied on Memory Directory**
   ```bash
   # Fix directory permissions
   chmod 755 memory/
   ```

3. **Missing Dependencies**
   ```bash
   # Reinstall backend dependencies
   cd server/backend
   pip install -r requirements.txt
   
   # Reinstall frontend dependencies
   cd server/frontend
   rm -rf node_modules package-lock.json
   npm install
   ```

4. **CORS Issues**
   - Ensure backend is running on port 8000
   - Frontend should be on port 5173
   - Check browser console for specific errors

### Logs and Debugging

1. **Backend Logs**
   - Server logs are printed to console
   - Check for API endpoint errors

2. **Frontend Logs**
   - Open browser developer tools
   - Check console for JavaScript errors
   - Network tab shows API request status

## 🔗 API Endpoints

### Memory Management

- `POST /upload-memory` - Upload memory file
- `GET /memories/{character}` - Get memories for character
- `GET /search-memories` - Search memories
- `DELETE /memory/{character}/{filename}` - Delete memory

### File Operations

- `GET /list-files` - List all memory files
- `GET /file-content/{path}` - Get file content
- `POST /create-file` - Create new file

## ✅ Success Verification

1. **Backend Status**
   ```bash
   curl http://localhost:8000/health
   ```
   Should return: `{"status": "healthy"}`

2. **Frontend Access**
   - Open http://localhost:5173 in browser
   - Should see MemU interface

3. **Full Workflow Test**
   - Upload a memory file
   - Browse memories
   - Search for content
   - View memory details

## 🎉 You're Ready!

The MemU server is now running with both backend and frontend services. You can:

- 📝 Create and manage memories
- 🔍 Search through memory content
- 👥 Organize memories by character
- 📊 View memory analytics
- 🔗 Link related memories

For more advanced configuration and API usage, see the main README. 