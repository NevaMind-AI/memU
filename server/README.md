# PersonaLab Backend Management System (React + Vite + FastAPI)

Modern PersonaLab backend management system with separated frontend and backend architecture, providing complete database management functionality.

## 🏗️ Architecture Overview

- **Frontend**: React 18 + Vite + Material-UI
- **Backend**: FastAPI + PostgreSQL + pgvector
- **Database**: PostgreSQL with pgvector extension
- **API Documentation**: Auto-generated OpenAPI/Swagger documentation

## 📁 Project Structure

```
server/
├── backend/                 # FastAPI backend
│   ├── main.py             # FastAPI main application
│   ├── start.py            # Startup script
│   └── requirements.txt    # Python dependencies
└── frontend/               # React frontend
    ├── src/
    │   ├── api/           # API client
    │   ├── components/    # React components
    │   ├── pages/         # Page components
    │   └── App.jsx        # Main application
    ├── package.json       # Node dependencies
    └── vite.config.js     # Vite configuration
```

## ✨ Features

### 📊 System Overview
- Real-time statistics display
- Conversation, memory, agent, and user data statistics
- Today and this week activity metrics

### 💬 Conversation Management
- Conversation list browsing and search
- Filter by agent and user
- Conversation details view (including complete message history)
- Conversation deletion functionality

### 🧠 Memory Management
- Memory list display and filtering
- Memory details view (Profile, Event, Mind content)
- Collapsible display of memory content
- Memory deletion functionality

### 📝 Operation Records
- Memory operation history tracking
- Create/update operation records
- Operation time and details display

### 🔍 Advanced Features
- Responsive design supporting mobile devices
- Real-time data loading
- Paginated browsing
- Error handling and user feedback
- Modern UI design

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- Node.js 16+
- PostgreSQL 12+ with pgvector extension
- PersonaLab project environment

### 1. Install Backend Dependencies

```bash
cd server/backend
pip install -r requirements.txt
```

### 2. Install Frontend Dependencies

```bash
cd server/frontend
npm install
```

### 3. Environment Configuration

Ensure the following environment variables are set (or in `.env` file in PersonaLab root directory):

```bash
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=personalab
POSTGRES_USER=chenhong
POSTGRES_PASSWORD=
```

### 4. Start Services

#### Start Backend API Server

```bash
cd server/backend
python start.py
```

Backend will run on `http://localhost:8080`

- API Interface: http://localhost:8080
- API Documentation: http://localhost:8080/docs
- Interactive API Documentation: http://localhost:8080/redoc

#### Start Frontend Development Server

```bash
cd server/frontend
npm run dev
```

Frontend will run on `http://localhost:5173`

### 5. Access Application

Open browser and visit `http://localhost:5173` to use the management system.

## 📚 API Documentation

### Main API Endpoints

- `GET /api/stats` - Get system statistics
- `GET /api/conversations` - Get conversation list
- `GET /api/conversations/{id}` - Get conversation details
- `DELETE /api/conversations/{id}` - Delete conversation
- `GET /api/memories` - Get memory list
- `GET /api/memories/{id}` - Get memory details
- `DELETE /api/memories/{id}` - Delete memory
- `GET /api/memory-operations` - Get memory operation records
- `GET /api/agents` - Get agent list
- `GET /api/users` - Get user list

All APIs support pagination and filter parameters. Detailed API documentation can be viewed by visiting `http://localhost:8080/docs`.

## 🛠️ Development Notes

### Frontend Development

- Use React Hooks for state management
- Material-UI component library provides consistent design language
- Axios for HTTP requests
- React Router for routing management
- Responsive design adapted to various screen sizes

### Backend Development

- FastAPI provides high-performance asynchronous API
- Pydantic for data validation
- PostgreSQL database integration
- Auto-generated API documentation
- CORS support for frontend-backend separation

### Database

- Compatible with existing PersonaLab database structure
- Support pgvector vector search functionality
- Direct SQL queries provide optimal performance

## 🔧 Configuration

### Backend Configuration

Backend automatically sets PostgreSQL environment variables with default configuration:
- Host: localhost
- Port: 5432
- Database: personalab
- User: chenhong
- Password: empty

### Frontend Configuration

Frontend API client configuration is in `src/api/client.js`, defaults to connecting to `http://localhost:8080`.

## 🐛 Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Confirm PostgreSQL service is running
   - Check database configuration is correct
   - Confirm pgvector extension is installed

2. **Frontend Cannot Connect to Backend**
   - Confirm backend server is running
   - Check CORS configuration
   - Confirm port is not occupied

3. **Dependency Installation Issues**
   - Confirm Python and Node.js versions meet requirements
   - Try clearing cache and reinstalling
   - Check network connection

## 📈 Performance Optimization

- Use connection pooling for database operations
- Implement frontend caching for static data
- Use pagination for large datasets
- Optimize SQL queries for better performance

## 🔒 Security Considerations

- Implement proper input validation
- Use parameterized queries to prevent SQL injection
- Add authentication middleware when needed
- Sanitize output data to prevent XSS attacks

## 📄 License

This project is part of PersonaLab and follows the same license terms.

## 🤝 Contributing

Please follow the PersonaLab contribution guidelines for development and submission. 