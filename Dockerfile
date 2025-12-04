# Use a newer, supported python image (Bookworm is Debian 12)
FROM python:3.9-slim-bookworm

# Install system dependencies
# Using apt-get is recommended for Dockerfiles, and rm -rf /var/lib/apt/lists/* reduces image size
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
