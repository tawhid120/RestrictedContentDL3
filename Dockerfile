# Change from python:3.9-slim-buster to python:3.10-slim-bookworm
FROM python:3.10-slim-bookworm

# Install system dependencies
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

# --- নতুন লাইন: ফ্লাস্ক (Flask) ইন্সটল করা হচ্ছে ---
RUN pip install flask
# ---------------------------------------------

# Copy rest of the bot files
COPY . .

# Make start.sh executable
RUN chmod +x start.sh

# Expose port for Flask
EXPOSE 8000

# --- পরিবর্তিত লাইন: start.sh এর বদলে web.py রান করা হচ্ছে ---
CMD ["python3", "web.py"]
# --------------------------------------------------------
