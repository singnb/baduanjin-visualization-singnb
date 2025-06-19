# Baduanjin Visualization - Backend API

> A FastAPI-based backend service for Baduanjin exercise analysis, user authentication, and audio processing capabilities.

## Table of Contents

- [Prerequisites](#prerequisites)
- [Getting Started](#getting-started)
- [Project Structure](#project-structure)
- [Environment Setup](#environment-setup)
- [Development](#development)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)
- [Additional Resources](#additional-resources)
- [Contributing](#contributing)
- [License](#license)

## Prerequisites

Before you begin, ensure you have the following installed on your system:

| Tool | Version | Download Link |
|------|---------|---------------|
| **Python** | 3.10.16 | [python.org](https://www.python.org/) |
| Conda/Anaconda | 24.9.2           | [anaconda.com](https://www.anaconda.com/) |
| **PostgreSQL** | 17 | [postgresql.org](https://www.postgresql.org/) |
| **Git** | 2.49.0.windows.1 | [git-scm.com](https://git-scm.com/) |

### Verify Installation

```bash
python --version
conda --version
psql --version
git --version
```

## Getting Started

### 1. Navigate to Backend Directory

Open PowerShell, Command Prompt, or Terminal:

```bash
cd path/to/your/backend
cd backend
```

### 2. Set Up Python Virtual Environment

#### Using Conda (Recommended)

```bash
# Activate your existing mmpose environment
conda activate C:\Users\singn\.conda\envs\mmpose_env

# Or create a new environment for this project
conda create -n baduanjin-backend python=3.9
conda activate baduanjin-backend
```

#### Using Virtual Environment (Alternative)

```bash
# Create virtual environment
python -m venv venv

# Activate virtual environment
# Windows
venv\Scripts\activate
# macOS/Linux
source venv/bin/activate
```

### 3. Install Dependencies

#### Core API Dependencies

```bash
pip install fastapi uvicorn sqlalchemy psycopg2-binary python-jose[cryptography] passlib[bcrypt] python-multipart pydantic[email] python-dotenv jwt
```

#### Audio Processing Dependencies

```bash
pip install moviepy SpeechRecognition googletrans==4.0.0-rc1 gTTS pydub decorator imageio tqdm numpy pillow proglog requests
```

#### Package Descriptions

| Category | Package | Purpose |
|----------|---------|---------|
| **API Framework** | `fastapi` | Modern web framework for building APIs |
| | `uvicorn` | ASGI server for running FastAPI |
| **Database** | `sqlalchemy` | SQL toolkit and ORM |
| | `psycopg2-binary` | PostgreSQL adapter for Python |
| **Authentication** | `python-jose[cryptography]` | JWT token handling |
| | `passlib[bcrypt]` | Password hashing |
| | `jwt` | JSON Web Token implementation |
| **Audio Processing** | `moviepy` | Video and audio editing |
| | `SpeechRecognition` | Speech-to-text conversion |
| | `googletrans` | Google Translate API |
| | `gTTS` | Google Text-to-Speech |
| | `pydub` | Audio manipulation |
| **Utilities** | `python-multipart` | Form data handling |
| | `pydantic[email]` | Data validation with email support |
| | `python-dotenv` | Environment variable management |

#### Install All Dependencies:
```bash
pip install -r requirements.txt
```

## Project Structure

```
backend/
├── auth/                  # Authentication module
│   └── router.py          # Authentication routes and endpoints
├── ml_models/             # Machine Learning models and configurations
│   ├── detection/         # Pose detection models
│   │   ├── faster_rcnn_r50_fpn_1x_coco_20200130-047c8118.pth
│   │   └── hrnet_w32_coco_256x192-c78dce93_20200708.pth
│   └── pose/              # Pose estimation models
│       └── simple_topdown_hrnet.py
├── ml_pipeline/           # Machine Learning processing pipeline
│   ├── config/            # ML configuration files
│   │   ├── td-hm_hrnet-w32_8xb64-210e_coco-256x192.py
│   │   └── faster_rcnn_r50_fpn_coco.py
│   ├── demo/              # Demo and example files
│   │   └── topdown_demo_mmdet_no_heatmap.py
│   ├── extract_json_files.py    # JSON data extraction
│   ├── mandarin_to_english.py   # Language translation service
│   ├── pose_analyzer.py         # Pose analysis logic
│   └── results_analysis.py      # Analysis results processing
├── routers/               # FastAPI route handlers
│   ├── analysis.py        # Analysis endpoints
│   ├── analysis_with_master.py  # Master-learner analysis
│   ├── relationships.py   # Relationship management
│   ├── video.py           # Video processing endpoints
│   └── video_english.py   # English video processing
├── services/              # Business logic services
│   └── 📄 video_processor.py # Video processing service
├── utils/                 # Utility functions
│   └── security.py        # Security and authentication utilities
├── uploads/               # User uploaded files storage
│   ├── 1/                 # User session uploads
│   └── 2/                 # User session uploads
├── outputs_json/          # Analysis results and output data
│   ├── baduanjin_analysis/  # Baduanjin analysis results
│   │   ├── learner_balance.json
│   │   ├── learner_joint_angles.json
│   │   ├── learner_recommendations.json
│   │   ├── learner_smoothness.json
│   │   ├── learner_symmetry.json
│   │   ├── balance_metrics.png
│   │   ├── com_trajectory.png
│   │   ├── joint_angles.png
│   │   ├── movement_smoothness.png
│   │   ├── movement_symmetry.png
│   │   └── key_poses.png
│   ├── 1/               # Session-specific results
│   └── 2/               # Session-specific results
├── create_db.py         # Database initialization script
├── database.py          # Database configuration and connection
├── main.py              # FastAPI application entry point
├── models.py            # SQLAlchemy database models
├── schemas.py           # Pydantic request/response schemas
├── requirements.txt     # Python dependencies
├── .env.example         # Environment variables template
└── README.md            # Project documentation
```

## Environment Setup

Create a `.env` file in the backend root directory:

```bash
# .env
# Database Configuration
DATABASE_URL=postgresql://username:password@localhost:5432/baduanjin_db
DB_HOST=localhost
DB_PORT=5432
DB_NAME=baduanjin_db
DB_USER=your_username
DB_PASSWORD=your_password

## Development

### Start the Development Server

```bash
# Make sure you're in the backend directory and virtual environment is activated
uvicorn main:app --reload
```

**This will:**
- Start the FastAPI server on `http://localhost:8000`
- Enable auto-reload on code changes
- Provide interactive API documentation at `http://localhost:8000/docs`

## API Documentation

Once the server is running, you can access:

| Resource | URL | Description |
|----------|-----|-------------|
| **Interactive Docs** | `http://localhost:8000/docs` | Swagger UI documentation |
| **ReDoc** | `http://localhost:8000/redoc` | Alternative documentation |
| **OpenAPI Schema** | `http://localhost:8000/openapi.json` | Raw OpenAPI schema |

### Main API Endpoints

```
POST   /auth/login                    # User authentication
POST   /auth/register                 # User registration
POST   /analysis/upload               # Upload Baduanjin exercise video
GET    /analysis/results              # Get analysis results
POST   /analysis/with-master          # Master-learner analysis comparison
POST   /video/process                 # Process video files
POST   /video/english                 # Process video with English output
GET    /relationships                 # Get learner-master relationships
POST   /relationships                 # Create learner-master relationship
```

## Additional Resources

| Resource | Link |
|----------|------|
| FastAPI Documentation | [fastapi.tiangolo.com](https://fastapi.tiangolo.com/) |
| SQLAlchemy Documentation | [sqlalchemy.org](https://www.sqlalchemy.org/) |
| PostgreSQL Documentation | [postgresql.org/docs](https://www.postgresql.org/docs/) |
| Pydantic Documentation | [pydantic-docs.helpmanual.io](https://pydantic-docs.helpmanual.io/) |
| JWT Documentation | [jwt.io](https://jwt.io/) |

## License
```bash
This project is licensed under the MIT License.
```
