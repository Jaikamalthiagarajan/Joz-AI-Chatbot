# Joz AI - HR Chatbot

An intelligent HR assistant chatbot built with FastAPI and AI-powered capabilities. This application provides employees with quick access to HR policies, leave requests, and employee information through a conversational interface.

## Features

- **AI-Powered Chat**: Ask questions about HR policies, leave requests, and employee data
- **Document Processing**: Upload and process HR policy documents
- **Leave Management**: Request and manage leaves with automated workflows
- **Employee Database**: Access employee information and records
- **Authentication**: Secure JWT-based authentication
- **Vector Search**: Advanced semantic search using ChromaDB and embeddings
- **Policy QA**: Question-answering system trained on company HR policies

## Tech Stack

### Backend
- **FastAPI** - Modern Python web framework
- **SQLAlchemy** - ORM for database operations
- **PostgreSQL** - Relational database
- **ChromaDB** - Vector database for semantic search
- **OpenAI API** - GPT integration for LLM capabilities
- **Google Generative AI** - Gemini API for content generation
- **python-jose** - JWT token handling
- **passlib** - Password hashing

### Frontend
- **React.js** - UI framework
- **CSS** - Styling

## Prerequisites

- Python 3.8+
- PostgreSQL 12+
- Node.js 14+ (for frontend)
- API Keys:
  - OpenAI API key
  - Google Generative AI API key

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/Jaikamalthiagarajan/Joz-AI-Chatbot.git
cd Joz-AI-Chatbot
```

### 2. Set Up Python Virtual Environment

```bash
python -m venv env
source env/bin/activate  # On Windows: env\Scripts\activate
```

### 3. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the `.env.example` file to `.env` and fill in your actual credentials:

```bash
cp .env.example .env
```

Edit `.env` and add your configuration:

```
# Database Configuration
DATABASE_URL=postgresql://postgres:your_password@localhost:5432/Joz_AI_DB

# API Keys
OPENAI_API_KEY=your_openai_api_key
GOOGLE_API_KEY=your_google_generative_ai_key

# JWT Secret
SECRET_KEY=your_secret_key_here

# Token Settings
ACCESS_TOKEN_EXPIRE_MINUTES=60
```

### 5. Set Up PostgreSQL Database

```bash
# Create database
createdb Joz_AI_DB

# Update DATABASE_URL in .env with your PostgreSQL credentials
```

### 6. Run Database Migrations

```bash
# The database tables will be created automatically on first run
```

### 7. Install Frontend Dependencies

```bash
cd frontend
npm install
```

## Running the Application

### Backend

```bash
# Navigate to project root
cd /path/to/Joz-AI-Chatbot

# Activate virtual environment
source env/bin/activate

# Run FastAPI server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`
API documentation: `http://localhost:8000/docs`

### Frontend

In a new terminal:

```bash
cd frontend

# Copy environment template
cp .env.example .env

# Edit .env and set your API URL (if different from default)
# REACT_APP_API_URL=http://localhost:8000

# Install dependencies and start
npm install
npm start
```

The frontend will be available at `http://localhost:3000`

## Project Structure

```
Joz_AI/
├── app/                          # Main application package
│   ├── main.py                   # FastAPI application entry point
│   ├── auth/                     # Authentication module
│   │   ├── models.py
│   │   └── routes.py
│   ├── chat/                     # Chat/Policy QA module
│   │   └── routes.py
│   ├── core/                     # Core configuration
│   │   ├── config.py            # Configuration and environment variables
│   │   ├── database.py          # Database setup and session management
│   │   ├── deps.py              # Dependency injection
│   │   └── security.py          # JWT token handling
│   ├── documents/               # Document processing
│   │   ├── chunker.py           # Text chunking utilities
│   │   └── parser.py            # PDF/Document parsing
│   ├── hr/                       # HR management module
│   │   ├── report_generator.py  # Report generation
│   │   ├── routes.py
│   │   └── services.py
│   ├── llm/                      # LLM integration
│   │   ├── embeddings.py        # Text embeddings
│   │   └── llm_services.py      # LLM service wrapper
│   ├── models/                   # Database models
│   │   ├── employee.py
│   │   ├── leave_request.py
│   │   └── user.py
│   ├── user/                     # User management module
│   │   └── routes.py
│   └── vectorstore/             # Vector database client
│       └── chroma_client.py
├── frontend/                     # React frontend
│   ├── src/
│   │   ├── App.js
│   │   ├── index.js
│   │   ├── components/
│   │   │   └── Navbar.js
│   │   └── pages/
│   │       ├── ChatPage.js
│   │       ├── DashboardPage.js
│   │       ├── HRManagementPage.js
│   │       ├── LeaveRequestPage.js
│   │       └── LoginPage.js
│   └── package.json
├── data/                         # Data directory
│   └── chroma_db/               # Vector database storage
├── uploaded_policies/            # User-uploaded HR policies
├── requirements.txt              # Python dependencies
├── .env.example                  # Example environment variables
└── README.md                     # This file
```

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - User login
- `POST /auth/logout` - User logout

### Chat
- `POST /chat/query` - Ask questions about HR policies
- `POST /chat/policy-upload` - Upload new policy documents

### HR Management
- `GET /hr/employees` - Get employee list
- `GET /hr/employees/{id}` - Get employee details
- `POST /hr/report` - Generate HR reports

### Leave Management
- `POST /leave/request` - Submit leave request
- `GET /leave/requests` - Get leave requests
- `PUT /leave/requests/{id}` - Approve/reject leave request

### User
- `GET /user/profile` - Get user profile
- `PUT /user/profile` - Update user profile

## Environment Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `DATABASE_URL` | PostgreSQL connection string | `postgresql://user:pass@localhost:5432/dbname` |
| `OPENAI_API_KEY` | OpenAI API key for GPT integration | `sk-...` |
| `GOOGLE_API_KEY` | Google Generative AI API key | `AIzaSy...` |
| `SECRET_KEY` | JWT secret key | `your-secret-key-min-32-chars` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | JWT token expiration time | `60` |

**IMPORTANT**: Never commit `.env` file to version control. The `.env` file is already in `.gitignore`.

## Security Considerations

- All sensitive data (passwords, API keys) must be stored in `.env` file
- Never hardcode credentials in the codebase
- Use strong `SECRET_KEY` for JWT tokens
- Enable HTTPS in production
- Validate and sanitize all user inputs
- Keep dependencies updated regularly

## Database Schema

The application uses SQLAlchemy ORM. Key models include:

- **User** - Application users with authentication
- **Employee** - Employee records
- **LeaveRequest** - Leave request management
- **HRPolicy** - Stored HR policies

## Document Upload

To upload HR policy documents:

1. Go to the HR Management section
2. Click "Upload Policy"
3. Select PDF or DOCX files
4. The documents will be automatically:
   - Parsed into text chunks
   - Converted to embeddings
   - Stored in ChromaDB for semantic search

## Troubleshooting

### Database Connection Error
- Ensure PostgreSQL is running
- Verify `DATABASE_URL` in `.env` is correct
- Check PostgreSQL user credentials

### API Key Errors
- Verify all API keys in `.env` are valid
- Check API key quotas and limits
- Ensure APIs are enabled in respective services

### Missing Dependencies
```bash
pip install -r requirements.txt --upgrade
```

### CORS Issues
- Ensure backend is running on `http://0.0.0.0:8000`
- Frontend configured to use correct API URL

## Contributing

1. Create a new branch for your feature
2. Make your changes and test thoroughly
3. Commit with clear messages
4. Push to your branch
5. Create a Pull Request

## License

This project is provided as-is for educational and internal use.

## Support

For issues, questions, or suggestions, please open an issue on GitHub.

## Changelog

### v1.0.0 (Initial Release)
- AI-powered HR chatbot
- Policy QA system
- Leave management
- Employee database
- JWT authentication

---

**Last Updated**: April 2026

**Note**: This is a sensitive HR application handling employee data. Ensure proper data protection and privacy measures are implemented in production.
