## Project Overview

This is a hierarchical agent teams system built with LangGraph that implements multi-agent collaboration for research and document generation tasks. The system uses a supervisor pattern to coordinate between different agent teams.

### Architecture

**Backend (Python/FastAPI)**
- **Main Graph** (`backend/graph.py`): Top-level supervisor that routes between research and document teams
- **Research Teams** (`backend/research_teams/`): Handles search and web scraping operations
- **Document Teams** (`backend/document_teams/`): Manages document writing, note-taking, and chart generation
- **Supervisor System** (`backend/utils/supervisor.py`): Implements LLM-based routing with fallback logic
- **Streaming Support**: Uses AsyncQueueCallbackHandler for real-time SSE responses

**Frontend (Vue.js/Vite)**
- Single-page Vue application with SSE chat interface
- Proxy configuration routes `/api` requests to backend on port 8000

**Key Dependencies**
- LangGraph for agent orchestration
- FastAPI for REST API and SSE streaming
- Vue 3 with Vite for frontend
- Anthropic/OpenAI compatible models (configured for Bailian/DashScope)

## Development Commands

### Backend Setup
```bash
cd backend
pip install -r requirements.txt
# Copy and configure environment
cp .env.example .env
# Edit .env with your API credentials
uvicorn app:app --reload --port 8000
```

### Frontend Setup
```bash
cd frontend
npm install
npm run dev  # Starts on port 5173 with API proxy
```

### Production Build
```bash
# Frontend
cd frontend
npm run build

# Backend
cd backend
uvicorn app:app --host 0.0.0.0 --port 8000
```

## Environment Configuration

Required environment variables in `backend/.env`:
- `BAILIAN_API_KEY`: API key for the language model
- `BAILIAN_BASE_URL`: API endpoint (defaults to DashScope compatible mode)
- `BAILIAN_MODEL`: Model name (defaults to Moonshot-Kimi-K2-Instruct)

## Agent System Architecture

The system implements a three-tier hierarchy:

1. **Super Graph** (`backend/graph.py:10`): Routes between research_team and writing_team
2. **Team Graphs**: Each team has its own supervisor and specialized agents
3. **Individual Agents**: Specific tools and responsibilities within each team

**State Management**
- Uses `MessagesState` with progress flags (`research_done`, `writing_done`)
- Commands flow through supervisor nodes that determine next actions
- Context tracking via `backend/utils/context.py` for request-scoped state

**Streaming Implementation**
- Real-time updates via Server-Sent Events (SSE)
- `AsyncQueueCallbackHandler` bridges LangGraph execution to HTTP streaming
- Steps summarization for frontend consumption