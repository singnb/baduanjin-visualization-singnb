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
└── README.md               # Main README
```
## Quick Start

### Prerequisites
- Node.js 14+ and npm
- Python 3.8+
- PostgreSQL
- Git

### Frontend Setup
```bash
cd frontend
npm install
npm start

The frontend will be available at http://localhost:3000
```
### Backend Setup
```bash
bashcd backend
pip install -r requirements.txt
uvicorn main:app --reload
The API will be available at http://localhost:8000
```

### Documentation
```bash
Frontend Documentation
Backend Documentation
```

## License
```bash
This project is licensed under the MIT License.
```
