# Baduanjin Visualization System

A comprehensive system for analyzing and visualizing Baduanjin exercise movements using computer vision and machine learning.

## Project Structure
```
baduanjin-visualization/
├── frontend/              # React frontend application
│   ├── src/
│   ├── public/
│   ├── package.json
│   └── README.md
├── backend/               # FastAPI backend API
│   ├── auth/
│   ├── ml_models/
│   ├── routers/
│   ├── main.py
│   ├── requirements.txt
│   └── README.md
├── pi-service/            # pi-service backend API
│   ├── app/
│   ├── pi_requirements.txt
│   ├── startup.py
│   └── README.md
└── README.md               # Main README
```
## Quick Start

### Prerequisites
- Node.js 14+ and npm
- Python 3.10+
- PostgreSQL
- Git
- Azure cloud

### Frontend Setup
```bash
cd frontend_folder
npm install
npm start

The frontend will be available at http://localhost:3000
Alternatively, use Azure frontend URL (skip above steps)
```
### Backend Setup
```bash
cd backend_folder
pip install -r requirements.txt
uvicorn main:app --reload

The API will be available at http://localhost:8000
Alternatively, use Azure backend URL (skip above steps)
```

## License
```bash
This project is licensed under the MIT License.
```
