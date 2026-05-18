FROM python:3.10-slim

WORKDIR /app

# Install system dependencies
# libsndfile1  — required by librosa/soundfile for audio decoding
# ffmpeg       — required for MP3/WAV/OGG decoding
RUN apt-get update && apt-get install -y \
    build-essential \
    libsndfile1 \
    ffmpeg \
    --no-install-recommends \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies first (Docker layer cache)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copy application code and assets
COPY . .

# Ensure assets directory exists
RUN mkdir -p assets/images

# Suppress TF/TFLite noise in logs
ENV PYTHONUNBUFFERED=1
ENV TF_CPP_MIN_LOG_LEVEL=3

# Render.com passes the port via $PORT — fall back to 8501 locally
EXPOSE 8501

CMD streamlit run app.py \
    --server.port=${PORT:-8501} \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --browser.gatherUsageStats=false
