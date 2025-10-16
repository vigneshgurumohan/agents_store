# 🤖 Agents Marketplace

A comprehensive AI agents marketplace built with FastAPI and vanilla HTML/CSS/JS. This platform allows users to browse, discover, and explore AI-powered solutions while supporting ISVs (Independent Software Vendors), Resellers, and Admin management with complete authentication and profile systems.

## 🌟 Features

### **🤖 AI Agents**
- **28 AI Agents** across multiple categories (Conversational AI, Data Analytics, Document Intelligence, etc.)
- **Individual Agent Pages** with detailed information, demo assets, and deployment options
- **Responsive Design** with modern UI/UX
- **Tabbed Interface** for organized information display

### **👥 User Management**
- **ISV System**: Registration, login, profile management, agent management
- **Reseller System**: Registration, login, profile management with whitelisted domains
- **Admin Panel**: Complete management of ISVs and Resellers with approval workflows
- **Role-based Authentication**: ISV, Reseller, Admin roles with secure login

### **🔧 Technical Features**
- **Real-time Data** from CSV sources with PostgreSQL support
- **RESTful API** with comprehensive documentation
- **Data Persistence**: All user data saved to CSV files
- **Deployment Ready**: Optimized for Git and Render deployment

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
│   │   ├── auth.csv              # User authentication data
│   │   ├── capabilities_mapping.csv
│   │   ├── demo_assets.csv
│   │   ├── deployments.csv
│   │   ├── docs.csv
│   │   ├── isv.csv               # ISV company data
│   │   └── reseller.csv          # Reseller company data
│   ├── config.py                 # Configuration settings
│   ├── data_source.py           # Data access layer
│   ├── main.py                  # FastAPI application
│   ├── start_server.py          # Development server
│   ├── start_production.py      # Production server
│   ├── requirements.txt         # Python dependencies
│   └── test_registration.py     # Registration testing script
├── frontend/
│   ├── index.html               # Agents listing page
│   ├── agent.html               # Individual agent page
│   ├── isv_login.html           # ISV login page
│   ├── isv_signup.html          # ISV registration page
│   ├── isv_profile.html         # ISV profile page
│   ├── reseller_login.html      # Reseller login page
│   ├── reseller_signup.html     # Reseller registration page
│   ├── reseller_profile.html    # Reseller profile page
│   ├── admin_login.html         # Admin login page
│   ├── admin_isv.html           # Admin ISV management
│   ├── admin_reseller.html      # Admin reseller management
│   ├── admin_agents.html        # Admin agent management
│   └── agent_onboard.html       # Agent onboarding page
├── .gitignore
├── env.example                  # Environment variables template
├── render.yaml                  # Render deployment config
├── DEPLOYMENT.md                # Deployment guide
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

### **🤖 Agent APIs**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | System health check |
| `/api/agents` | GET | List all agents |
| `/api/agents/{agent_id}` | GET | Get detailed agent information |
| `/api/capabilities` | GET | Get capabilities mapping |

### **🔐 Authentication APIs**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/login` | POST | Universal login (ISV/Reseller/Admin) |
| `/api/auth/signup` | POST | Universal signup (ISV/Reseller) |

### **🏢 ISV APIs**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/isv/profile/{isv_id}` | GET | Get ISV profile with statistics |
| `/api/isv/profile/{isv_id}` | PUT | Update ISV profile |
| `/api/admin/isvs` | GET | Admin: List all ISVs |
| `/api/admin/isvs/{isv_id}` | PUT | Admin: Update any ISV |

### **🏪 Reseller APIs**
| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/reseller/profile/{reseller_id}` | GET | Get reseller profile with statistics |
| `/api/reseller/profile/{reseller_id}` | PUT | Update reseller profile |
| `/api/admin/resellers` | GET | Admin: List all resellers |
| `/api/admin/resellers/{reseller_id}` | PUT | Admin: Update any reseller |

### **🌐 Frontend Pages**
| Endpoint | Description |
|----------|-------------|
| `/agents` | Agents listing page |
| `/agent/{agent_name}` | Individual agent page |
| `/isv/login` | ISV login page |
| `/isv/signup` | ISV registration page |
| `/isv/profile/{isv_id}` | ISV profile page |
| `/reseller/login` | Reseller login page |
| `/reseller/signup` | Reseller registration page |
| `/reseller/profile/{reseller_id}` | Reseller profile page |
| `/admin/login` | Admin login page |
| `/admin/isv` | Admin ISV management |
| `/admin/reseller` | Admin reseller management |
| `/admin/agents` | Admin agent management |

## 🎨 Frontend Pages

### **🤖 Agent Pages**
#### Agents Listing (`/agents`)
- Grid layout with agent cards
- Agent type, persona, and value proposition
- Direct links to individual agent pages

#### Individual Agent Page (`/agent/{agent_name}`)
- **Overview Tab**: Basic information, features, ROI, description
- **Capabilities Tab**: All agent capabilities with badges
- **Deployments Tab**: Deployment options grouped by capability
- **Demo Assets Tab**: Inline images and videos
- **Documentation Tab**: SDK, swagger, samples, security details
- **Provider Info Tab**: ISV information

### **🏢 ISV Pages**
#### ISV Login (`/isv/login`)
- Email and password authentication
- Demo credentials provided
- Redirects to ISV profile after login

#### ISV Registration (`/isv/signup`)
- Company name, email, password, address, domain, mobile
- Admin approval workflow
- Automatic ID generation

#### ISV Profile (`/isv/profile/{isv_id}`)
- **Overview Tab**: Company info, statistics, approval status
- **My Agents Tab**: All agents created by the ISV
- **Edit Tab**: Update company information

### **🏪 Reseller Pages**
#### Reseller Login (`/reseller/login`)
- Email and password authentication
- Demo credentials provided
- Redirects to reseller profile after login

#### Reseller Registration (`/reseller/signup`)
- Company name, email, password, address, domain, mobile, whitelisted domain
- Admin approval workflow
- Automatic ID generation

#### Reseller Profile (`/reseller/profile/{reseller_id}`)
- **Overview Tab**: Company info, whitelisted domain, approval status
- **Edit Tab**: Update company information including whitelisted domain

### **🛡️ Admin Pages**
#### Admin Login (`/admin/login`)
- Dedicated admin login page
- Role-based access control
- Demo credentials provided
- Redirects to admin dashboard after login

#### Admin ISV Management (`/admin/isv`)
- View all ISVs with statistics
- Approve/reject ISV accounts
- Edit any ISV data
- Dashboard with key metrics

#### Admin Reseller Management (`/admin/reseller`)
- View all resellers with statistics
- Approve/reject reseller accounts
- Edit any reseller data including whitelisted domains
- Dashboard with key metrics

#### Admin Agent Management (`/admin/agents`)
- View all agents with approval status
- Approve/reject agent submissions
- Agent statistics and overview
- Link to agent detail pages

## 🚀 Deployment

### Render Deployment

1. **Connect your GitHub repository to Render**

2. **Create a new Web Service**
   - **Build Command**: `cd backend && pip install -r requirements.txt`
   - **Start Command**: `cd backend && python start_production.py`
   - **Environment**: Python 3

3. **Set Environment Variables** (optional)
   - `DATA_SOURCE`: Set to `postgres` if using database
   - Database credentials if using PostgreSQL

4. **Deploy**
   - Render will automatically deploy from your main branch

**Note**: Use `start_production.py` for production deployment as it's optimized for server environments.

### Manual Deployment

```bash
# Install dependencies
pip install -r backend/requirements.txt

# Set environment variables
export DATA_SOURCE=csv
export API_HOST=0.0.0.0
export API_PORT=8000

# Start the server (development)
cd backend
python start_server.py

# Or start production server
python start_production.py
```

## 🧪 Testing

### Registration Testing

```bash
cd backend
python test_registration.py
```

### Manual Testing

#### **🤖 Agent APIs**
1. **Health Check**: `curl http://localhost:8000/api/health`
2. **List Agents**: `curl http://localhost:8000/api/agents`
3. **Get Agent**: `curl http://localhost:8000/api/agents/agent_001`

#### **👥 User Management**
1. **ISV Login**: `curl -X POST http://localhost:8000/api/auth/login -d "email=babu@crayondata.com&password=password123"`
2. **Reseller Login**: `curl -X POST http://localhost:8000/api/auth/login -d "email=contact@redington.com&password=redington123"`
3. **Admin Login**: `curl -X POST http://localhost:8000/api/auth/login -d "email=admin@marketplace.com&password=admin123"`

## 🔑 Demo Credentials

### **ISV Account**
- **Email**: `babu@crayondata.com`
- **Password**: `password123`
- **Profile**: `/isv/profile/isv_001`

### **Reseller Account**
- **Email**: `contact@redington.com`
- **Password**: `redington123`
- **Profile**: `/reseller/profile/reseller_001`

### **Admin Account**
- **Email**: `admin@marketplace.com`
- **Password**: `admin123`
- **Dashboard**: `/admin/isv` or `/admin/reseller`

## 📈 Data Model

### Core Entities

- **Agents**: AI solutions with capabilities, descriptions, and metadata
- **Capabilities**: AI capabilities (Conversational AI, Data Analytics, etc.)
- **Deployments**: Service providers and deployment options
- **Demo Assets**: Images, videos, and demo links
- **ISVs**: Independent Software Vendors with agent management
- **Resellers**: Reseller companies with whitelisted domains
- **Auth**: User authentication with role-based access (ISV, Reseller, Admin)
- **Documentation**: SDK details, API docs, samples

### Relationships

- Agents → Capabilities (Many-to-Many)
- Agents → Demo Assets (One-to-Many)
- Agents → Documentation (One-to-Many)
- Agents → ISVs (Many-to-One)
- Capabilities → Deployments (One-to-Many)
- Auth → ISVs/Resellers (One-to-One via user_id)

### Data Storage

- **CSV Files**: All data stored in `backend/data/` directory
- **Real-time Updates**: Changes saved immediately to CSV files
- **ID Generation**: Sequential IDs following existing patterns (isv_001, reseller_001, auth_001)

## 🛠️ Development

### Adding New Agents

1. Add agent data to `backend/data/agents.csv`
2. Add capabilities mapping to `backend/data/capabilities_mapping.csv`
3. Add demo assets to `backend/data/demo_assets.csv`
4. Add documentation to `backend/data/docs.csv`

### Adding New Users

1. **ISV Registration**: Use `/isv/signup` or `/api/auth/signup` with `role=isv`
2. **Reseller Registration**: Use `/reseller/signup` or `/api/auth/signup` with `role=reseller`
3. **Admin Access**: Add directly to `backend/data/auth.csv` with `role=admin`

### Extending the API

1. Add new endpoints in `backend/main.py`
2. Add data access methods in `backend/data_source.py`
3. Update frontend JavaScript in respective HTML files
4. Add new frontend pages in `frontend/` directory

### Data Persistence

- All user data is automatically saved to CSV files
- Use `data_source.save_*_data()` methods for new records
- Use `data_source.update_*_data()` methods for updates
- ID generation follows existing patterns for consistency

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
- Review the registration test suite in `backend/test_registration.py`
- Check deployment guide in `DEPLOYMENT.md`

## 🎯 User Workflows

### **🏢 ISV Workflow**
1. **Register** → `/isv/signup` → Admin approval required
2. **Login** → `/isv/login` → Access profile dashboard
3. **Manage Profile** → Update company information
4. **View Agents** → See all agents created by ISV

### **🏪 Reseller Workflow**
1. **Register** → `/reseller/signup` → Admin approval required
2. **Login** → `/reseller/login` → Access profile dashboard
3. **Manage Profile** → Update company info and whitelisted domain
4. **View Status** → Check approval status

### **🛡️ Admin Workflow**
1. **Login** → `/admin/login` → Use admin credentials → Access admin panel
2. **Manage ISVs** → `/admin/isv` → Approve/reject ISV accounts
3. **Manage Resellers** → `/admin/reseller` → Approve/reject reseller accounts
4. **Manage Agents** → `/admin/agents` → Approve/reject agent submissions
5. **Edit Data** → Update any user information as needed

---

**Built with ❤️ using FastAPI and modern web technologies**

**Features**: AI Agents Marketplace • ISV Management • Reseller Management • Admin Panel • Role-based Authentication • Data Persistence
