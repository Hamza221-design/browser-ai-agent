FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    wget \
    gnupg \
    && wget -q -O - https://dl.google.com/linux/linux_signing_key.pub | gpg --dearmor -o /usr/share/keyrings/google-chrome.gpg \
    && echo "deb [arch=amd64 signed-by=/usr/share/keyrings/google-chrome.gpg] http://dl.google.com/linux/chrome/deb/ stable main" | tee /etc/apt/sources.list.d/google-chrome.list \
    && apt-get update \
    && apt-get install -y \
    google-chrome-stable \
    fonts-ipafont-gothic \
    fonts-wqy-zenhei \
    fonts-thai-tlwg \
    fonts-freefont-ttf \
    libxss1 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright browsers
RUN playwright install chromium
# RUN playwright install-deps

# Copy application code
COPY . .

# Create logs directory
RUN mkdir -p /app/logs

# Create db directory with proper permissions
RUN mkdir -p /app/db && chmod 777 /app/db

# Create chroma_models directory for caching ONNX models
RUN mkdir -p /app/db/chroma_models && chmod 777 /app/db/chroma_models

# Copy environment file
COPY config.env /app/config.env

# Expose port
EXPOSE 8000

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Switch to non-root user (commented out to avoid permission issues)
# USER appuser

# Run the application
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
