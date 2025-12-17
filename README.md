# RFP-Optimize AI Portal

A comprehensive AI-powered RFP (Request for Proposal) analysis and optimization platform built with FastAPI, Streamlit, and Google Gemini AI.

## 🚀 Features

### Core Functionality
- **User Authentication**: Secure registration and login system
- **RFP Management**: Create, view, and manage RFPs with detailed descriptions
- **AI-Powered Analysis**: Intelligent RFP analysis with recommendations and suggestions
- **Role-Based Access**: Separate permissions for clients and administrators
- **Real-time Dashboard**: Interactive dashboard with analytics and insights

### AI Analysis Features
- **Technical Specification Extraction**: Automatically identifies product types, voltage ratings, materials, and compliance standards
- **Win Probability Calculation**: AI-driven probability assessment based on match scores and margins
- **Financial Analysis**: Cost breakdowns, pricing recommendations, and margin calculations
- **Smart Recommendations**: Actionable suggestions for RFP optimization
- **Fallback Mode**: Works without API keys using realistic mock data

## 🛠️ Quick Start

### Prerequisites
- Python 3.8+
- pip package manager

### Installation

1. **Clone or download the project files**

2. **Install dependencies**:
   ```bash
   pip install fastapi uvicorn streamlit sqlalchemy python-dotenv python-multipart google-generativeai
   ```

3. **Run the portal**:
   ```bash
   python run_portal.py
   ```

   Or make it executable:
   ```bash
   chmod +x run_portal.py
   ./run_portal.py
   ```

### Access the Application

- **Main Application**: http://127.0.0.1:8501
- **API Documentation**: http://127.0.0.1:8000/docs
- **API Base URL**: http://127.0.0.1:8000

## 📋 Usage Guide

### Getting Started

1. **Register/Login**:
   - Create a new account or login with existing credentials
   - Choose role: `client` (default) or `admin`

2. **Create an RFP**:
   - Click "Create RFP" in the sidebar
   - Fill in title, detailed description, budget, and due date
   - Include technical specifications for better AI analysis

3. **Run AI Analysis**:
   - Click the "🚀 Run AI" button on any RFP
   - Wait for analysis to complete (1-3 seconds)
   - View results including recommendations and suggestions

### AI Analysis Results

Each RFP analysis provides:

- **Win Probability**: Percentage chance of winning the bid
- **Spec Match Score**: How well requirements match your capabilities
- **Extracted Specs**: Identified technical requirements
- **Financial Analysis**: Cost breakdowns and pricing recommendations
- **Recommendation**: Clear decision guidance (SELECT/CONSIDER/REVIEW/REJECT)
- **Suggestions**: Actionable improvement recommendations

### Example RFP Description

```
We require electrical infrastructure upgrade including:
- 11kV high voltage distribution system
- 415V low voltage panels and transformers
- XLPE cable laying for underground transmission
- IEC 60502 compliance standards

Budget: ₹150,000
Timeline: 3 months
```

## 🔧 Configuration

### Environment Variables (.env)

```env
# Google Gemini API Key (optional - works in demo mode without it)
GOOGLE_API_KEY=your_api_key_here
```

### Database

The application uses SQLite by default (`rfp_platform.db`). The database is automatically created and seeded when you run the portal.

## 🏗️ Architecture

### Backend (FastAPI)
- **main.py**: Main API server with endpoints for auth, RFPs, and AI analysis
- **models.py**: SQLAlchemy database models
- **schemas.py**: Pydantic data validation schemas
- **auth.py**: Authentication and authorization logic
- **ai_engine.py**: AI analysis orchestration (with mock fallback)
- **database.py**: Database connection and session management

### Frontend (Streamlit)
- **streamlit_app.py**: Main web application interface
- Interactive dashboard with real-time updates
- Role-based navigation and permissions

### AI Engine
- **AgentOrchestrator**: Coordinates technical and pricing analysis
- **TechnicalAgent**: Extracts specifications from RFP text
- **PricingAgent**: Calculates costs and margins
- **Mock Mode**: Realistic demo data without API calls

## 🔍 API Endpoints

### Authentication
- `POST /register` - User registration
- `POST /token` - User login (returns JWT token)

### RFP Management
- `POST /rfps` - Create new RFP
- `GET /rfps` - List user's RFPs
- `PUT /rfps/{id}` - Update RFP
- `POST /rfps/{id}/analyze` - Run AI analysis

### Admin Endpoints
- `GET /admin/rfps` - View all RFPs
- `GET /admin/rules` - Qualification rules
- `GET /admin/product-prices` - Product pricing data
- `GET /admin/test-prices` - Test pricing data

## 🐛 Troubleshooting

### Common Issues

1. **"Backend not reachable"**
   - Ensure both backend (port 8000) and frontend (port 8501) are running
   - Check that no other applications are using these ports

2. **"AI analysis failed"**
   - The system automatically falls back to mock mode
   - Check console output for detailed error messages

3. **Database errors**
   - Delete `rfp_platform.db` and restart to recreate the database
   - Ensure write permissions in the project directory

### Debug Mode

Run individual components for debugging:

```bash
# Backend only
python -m uvicorn main:app --host 127.0.0.1 --port 8000 --reload

# Frontend only
python -m streamlit run streamlit_app.py
```

## 📊 Demo Data

The portal comes pre-seeded with:
- Sample product prices and test fees
- Example qualification rules
- Mock AI analysis responses

## 🔒 Security

- JWT-based authentication
- Password hashing with secure algorithms
- Role-based access control
- CORS protection
- Input validation and sanitization

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

## 📄 License

This project is provided as-is for educational and demonstration purposes.

---

**Built with**: FastAPI, Streamlit, SQLAlchemy, Google Gemini AI
**Demo Mode**: Fully functional without external API keys