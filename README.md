# 🤖 Agents Marketplace

A modern AI agents marketplace built with FastAPI and vanilla HTML/CSS/JS. This platform allows users to browse, discover, and explore AI-powered solutions across various capabilities and use cases.

## 🌟 Features

- **28 AI Agents** across multiple categories (Conversational AI, Data Analytics, Document Intelligence, etc.)
- **Individual Agent Pages** with detailed information, demo assets, and deployment options
- **Responsive Design** with modern UI/UX
- **Tabbed Interface** for organized information display
- **Real-time Data** from CSV sources with PostgreSQL support
- **RESTful API** with comprehensive documentation

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- pip or conda

### Local Development

1. **Clone the repository**
   ```bash
   git clone <your-repo-url>
   cd agents-marketplace
   ```

2. **Install dependencies**
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. **Start the development server**
   ```bash
   python start_server.py
   ```

4. **Access the application**
   - **Frontend**: http://localhost:8000/agents
   - **API Docs**: http://localhost:8000/docs
   - **Health Check**: http://localhost:8000/api/health

## 📁 Project Structure

```
agents-marketplace/
├── backend/
│   ├── data/                     # CSV data files
│   │   ├── agents.csv
│   │   ├── capabilities_mapping.csv
│   │   ├── demo_assets.csv
│   │   ├── deployments.csv
│   │   ├── docs.csv
│   │   ├── isv.csv
│   │   └── reseller.csv
│   ├── config.py                 # Configuration settings
│   ├── data_source.py           # Data access layer
│   ├── main.py                  # FastAPI application
│   ├── start_server.py          # Development server
│   ├── requirements.txt         # Python dependencies
│   └── test_api.py              # API testing script
├── frontend/
│   ├── index.html               # Agents listing page
│   └── agent.html               # Individual agent page
├── .gitignore
├── render.yaml                  # Render deployment config
└── README.md
```

## 🔧 Configuration

### Environment Variables

Create a `.env` file in the backend directory:

```env
# Data Source Configuration
DATA_SOURCE=csv  # or "postgres" for database

# PostgreSQL Configuration (if using postgres)
DB_HOST=localhost
DB_PORT=5432
DB_NAME=agents_marketplace
DB_USER=postgres
DB_PASSWORD=your_password

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
```

### Data Source Options

1. **CSV Mode (Default)**: Uses CSV files in `backend/data/`
2. **PostgreSQL Mode**: Connects to a PostgreSQL database

## 📊 API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | System health check |
| `/api/agents` | GET | List all agents |
| `/api/agents/{agent_id}` | GET | Get detailed agent information |
| `/api/capabilities` | GET | Get capabilities mapping |
| `/agents` | GET | Agents listing page |
| `/agent/{agent_name}` | GET | Individual agent page |

## 🎨 Frontend Pages

### Agents Listing (`/agents`)
- Grid layout with agent cards
- Agent type, persona, and value proposition
- Direct links to individual agent pages

### Individual Agent Page (`/agent/{agent_name}`)
- **Overview Tab**: Basic information, features, ROI, description
- **Capabilities Tab**: All agent capabilities with badges
- **Deployments Tab**: Deployment options grouped by capability
- **Demo Assets Tab**: Inline images and videos
- **Documentation Tab**: SDK, swagger, samples, security details
- **Provider Info Tab**: ISV information

## 🚀 Deployment

### Render Deployment

1. **Connect your GitHub repository to Render**

2. **Create a new Web Service**
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && python start_server.py`
   - **Environment**: Python 3

3. **Set Environment Variables** (optional)
   - `DATA_SOURCE`: Set to `postgres` if using database
   - Database credentials if using PostgreSQL

4. **Deploy**
   - Render will automatically deploy from your main branch

### Manual Deployment

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
export DATA_SOURCE=csv
export API_HOST=0.0.0.0
export API_PORT=8000

# Start the server
cd backend
python start_server.py
```

## 🧪 Testing

### API Testing

```bash
cd backend
python test_api.py
```

### Manual Testing

1. **Health Check**: `curl http://localhost:8000/api/health`
2. **List Agents**: `curl http://localhost:8000/api/agents`
3. **Get Agent**: `curl http://localhost:8000/api/agents/agent_001`

## 📈 Data Model

### Core Entities

- **Agents**: AI solutions with capabilities, descriptions, and metadata
- **Capabilities**: AI capabilities (Conversational AI, Data Analytics, etc.)
- **Deployments**: Service providers and deployment options
- **Demo Assets**: Images, videos, and demo links
- **ISVs**: Independent Software Vendors
- **Documentation**: SDK details, API docs, samples

### Relationships

- Agents → Capabilities (Many-to-Many)
- Agents → Demo Assets (One-to-Many)
- Agents → Documentation (One-to-Many)
- Agents → ISVs (Many-to-One)
- Capabilities → Deployments (One-to-Many)

## 🛠️ Development

### Adding New Agents

1. Add agent data to `backend/data/agents.csv`
2. Add capabilities mapping to `backend/data/capabilities_mapping.csv`
3. Add demo assets to `backend/data/demo_assets.csv`
4. Add documentation to `backend/data/docs.csv`

### Extending the API

1. Add new endpoints in `backend/main.py`
2. Add data access methods in `backend/data_source.py`
3. Update frontend JavaScript in `frontend/agent.html`

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📝 License

This project is licensed under the MIT License.

## 🆘 Support

For support and questions:
- Create an issue in the GitHub repository
- Check the API documentation at `/docs` endpoint
- Review the test suite in `backend/test_api.py`

---

**Built with ❤️ using FastAPI and modern web technologies**
