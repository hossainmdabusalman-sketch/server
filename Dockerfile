FROM python:3.11-slim

# Install FFmpeg and other system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    libavcodec-extra \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY server.py .

# Expose port
EXPOSE 8000

# Run the application
CMD ["python", "-u", "server.py"]