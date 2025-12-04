# Change from python:3.9-slim-buster to python:3.10-slim-bookworm
FROM python:3.10-slim-bookworm

# Install system dependencies
# (Using bookworm repositories avoids the "exit code 100" apt error from older images)
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ffmpeg \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements and install them
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy rest of the bot files
COPY . .

# Make start.sh executable
RUN chmod +x start.sh

# Expose port for Flask
EXPOSE 8000

# Run the bot and Flask server
CMD ["bash", "start.sh"]
