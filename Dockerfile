FROM python:3.10-slim-bookworm

# Install system dependencies
# libssl-dev: tgcrypto-pyrofork compile করার জন্য দরকার
RUN apt-get update && apt-get install -y \
    git \
    curl \
    ffmpeg \
    gcc \
    python3-dev \
    libssl-dev \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

# ── স্পিড অপ্টিমাইজেশন: tgcrypto-pyrofork এবং uvloop ──
RUN pip install --no-cache-dir -r requirements.txt

RUN pip install flask

COPY . .

RUN chmod +x start.sh

EXPOSE 8000

CMD ["python3", "web.py"]
