# Use Python 3.10 slim to match your local environment
FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && \
 apt-get install -y --no-install-recommends \
 build-essential \
 cmake \
 libglib2.0-0 \
 libsm6 \
 libxext6 \
 libxrender-dev \
 libgomp1 \
 libgtk-3-0 \
 libjpeg62-turbo-dev \
 libpng-dev \
 libopencv-dev \
 wget \
 curl \
 ffmpeg \
 git \
 && apt-get clean \
 && rm -rf /var/lib/apt/lists/*

# Upgrade pip and install wheel
RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# ==== Install packages matching your localhost versions ====

# 1. Install numpy first (matches your localhost)
RUN pip install --no-cache-dir numpy==1.26.4

# 2. Install core scientific packages
RUN pip install --no-cache-dir \
 scipy==1.15.2 \
 pandas==2.2.3 \
 matplotlib==3.10.1

# 3. Install PyTorch (CPU version to match structure, but with newer versions)
RUN pip install --no-cache-dir \
 torch==2.0.0 \
 torchvision==0.15.1 \
 --index-url https://download.pytorch.org/whl/cpu

# 4. Install OpenCV (matches your localhost)
RUN pip install --no-cache-dir opencv-python==4.11.0.86

# 5. Install Pillow (matches your localhost)
RUN pip install --no-cache-dir Pillow==10.4.0

# 6. Install mmengine first (matches your localhost)
RUN pip install --no-cache-dir mmengine==0.10.7

# 7. Install mmcv (CRITICAL: matches your localhost version)
RUN pip install --no-cache-dir mmcv==2.0.1

# 8. Install mmdet (matches your localhost)
RUN pip install --no-cache-dir mmdet==3.3.0

# 9. Install mmpose (matches your localhost)
RUN pip install --no-cache-dir mmpose==1.3.2

# 10. Install web framework (matches your localhost)
RUN pip install --no-cache-dir \
 fastapi==0.115.12 \
 uvicorn[standard]==0.34.2

# 11. Install HTTP clients and core web dependencies
RUN pip install --no-cache-dir \
 httpx==0.13.3 \
 httpcore==0.9.1 \
 h11==0.9.0 \
 requests==2.28.2 \
 aiofiles==24.1.0

# 12. Install validation and settings
RUN pip install --no-cache-dir \
 pydantic==2.11.3 \
 pydantic_core==2.33.1 \
 pydantic-settings==2.9.1 \
 email_validator==2.2.0 \
 python-dotenv==1.1.0 \
 python-multipart==0.0.20

# 13. Install basic utilities
RUN pip install --no-cache-dir \
 click==8.1.8 \
 colorama==0.4.6 \
 tqdm==4.65.2 \
 rich==13.4.2 \
 termcolor==3.0.1 \
 tabulate==0.9.0

# 14. Install data processing utilities
RUN pip install --no-cache-dir \
 addict==2.4.0 \
 easydict==1.13 \
 joblib==1.4.2 \
 psutil==5.9.0 \
 py-cpuinfo==9.0.0

# 15. Install JSON and serialization
RUN pip install --no-cache-dir \
 json-tricks==3.17.3 \
 jsonschema==4.23.0 \
 jsonschema-specifications==2023.7.1 \
 PyYAML==6.0.2

# 16. Install ML/AI utilities
RUN pip install --no-cache-dir \
 scikit-learn==1.6.1 \
 seaborn==0.13.2 \
 pycocotools==2.0.8 \
 timm==0.1.20 \
 model-index==0.1.11

# 17. Install image/video processing
RUN pip install --no-cache-dir \
 imageio==2.37.0 \
 imageio-ffmpeg==0.6.0 \
 contourpy==1.3.2 \
 shapely==2.1.0

# 18. Install text and markup processing
RUN pip install --no-cache-dir \
 Markdown==3.8 \
 MarkupSafe==3.0.2 \
 Pygments==2.19.1

# 19. Install system and compatibility packages
RUN pip install --no-cache-dir \
 annotated-types==0.7.0 \
 anyio==4.7.0 \
 attrs==24.3.0 \
 certifi==2025.4.26 \
 charset-normalizer==3.3.2 \
 cycler==0.12.1 \
 exceptiongroup==1.2.0 \
 filelock==3.14.0 \
 fonttools==4.57.0 \
 fsspec==2025.3.2 \
 idna==2.10

# 20. Install additional utilities
RUN pip install --no-cache-dir \
 jmespath==0.10.0 \
 kiwisolver==1.4.8 \
 munkres==1.1.4 \
 natsort==8.4.0 \
 networkx==3.4.2 \
 packaging==24.2 \
 prettytable==3.16.0 \
 pycparser==2.21 \
 pyparsing==3.2.3

# 21. Install date/time and type utilities
RUN pip install --no-cache-dir \
 python-dateutil==2.9.0.post0 \
 pytz==2023.4 \
 six==1.17.0 \
 starlette==0.46.2 \
 sympy==1.13.3 \
 threadpoolctl==3.6.0 \
 tomli==2.2.1 \
 typing_extensions==4.13.2 \
 urllib3==1.26.20

# 22. Install Cython separately (can be problematic)
RUN pip install --no-cache-dir Cython==3.0.12

# 23. Install database support
RUN pip install --no-cache-dir \
 SQLAlchemy==2.0.40 \
 psycopg2-binary==2.9.10

# 24. Install authentication
RUN pip install --no-cache-dir \
 python-jose==3.4.0 \
 passlib==1.7.4 \
 PyJWT==2.10.1

# 25. Install Azure storage (matches your localhost)
RUN pip install --no-cache-dir azure-storage-blob==12.25.1

# 26. Install additional packages from your localhost
RUN pip install --no-cache-dir \
 openmim==0.3.9 \
 openxlab==0.1.2 \
 opendatalab==0.0.10

# Verify critical package versions match your localhost
RUN python -c "import numpy; print('NumPy version:', numpy.__version__); assert numpy.__version__ == '1.26.4'"
RUN python -c "import mmcv; print('MMCV version:', mmcv.__version__); assert mmcv.__version__ == '2.0.1'"
RUN python -c "import mmdet; print('MMDetection version:', mmdet.__version__); assert mmdet.__version__ == '3.3.0'"
RUN python -c "import mmpose; print('MMPose version:', mmpose.__version__); assert mmpose.__version__ == '1.3.2'"
RUN python -c "import mmengine; print('MMEngine version:', mmengine.__version__); assert mmengine.__version__ == '0.10.7'"
RUN python -c "import fastapi; print('FastAPI version:', fastapi.__version__)"
RUN python -c "import torch; print('PyTorch version:', torch.__version__)"
RUN python -c "import httpx; print('httpx version:', httpx.__version__)"

# Test mmpose import specifically
RUN python -c "from mmpose.apis import MMPoseInferencer; print('MMPose APIs import successful')"

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p uploads processed analysis outputs_json

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-m", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]