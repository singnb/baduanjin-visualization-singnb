# Baduanjin Visualization Backend - Requirements
# FastAPI and Web Framework
fastapi>=0.104.0
uvicorn[standard]>=0.24.0

# Database and ORM
sqlalchemy>=2.0.0
psycopg2-binary>=2.9.0

# Authentication and Security
python-jose[cryptography]>=3.3.0
passlib[bcrypt]>=1.7.4
jwt>=1.3.1
python-multipart>=0.0.6

# Data Validation and Configuration
pydantic[email]>=2.5.0
python-dotenv>=1.0.0
email-validator>=2.1.0

# Audio Processing
moviepy>=2.1.0
SpeechRecognition>=3.14.0
googletrans==4.0.0-rc1
gTTS>=2.5.0
pydub>=0.25.0

# Machine Learning and Computer Vision
torch>=1.11.0
torchvision>=0.12.0
opencv-python>=4.5.0
mmpose>=0.29.0
mmdet>=2.25.0
mmcv>=1.7.0

# Image and Media Processing
imageio>=2.30.0
imageio-ffmpeg>=0.6.0
pillow>=10.0.0
proglog>=0.1.10

# Utility Libraries
decorator>=5.1.0
tqdm>=4.65.0
numpy>=1.24.0
requests>=2.31.0

# HTTP and Networking
httpx>=0.25.0
httpcore>=1.0.0

# Data Processing
pandas>=1.5.0
matplotlib>=3.6.0
seaborn>=0.12.0
scipy>=1.9.0

# Development and Testing
pytest>=7.4.0
pytest-asyncio>=0.21.0
black>=23.0.0
flake8>=6.0.0
mypy>=1.5.0

# Additional FastAPI utilities
aiofiles>=23.0.0
Jinja2>=3.1.0