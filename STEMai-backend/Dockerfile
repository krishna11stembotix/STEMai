FROM python:3.11-slim
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
WORKDIR /app

# ✅ System dependencies + compilers for Programming Lab
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    nodejs \
    ffmpeg \
    xvfb \
    x11-utils \
    wget \
    curl \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libnss3 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libgtk-3-0 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libgbm1 \
    libasound2 \
    libpangocairo-1.0-0 \
    libpango-1.0-0 \
    libcups2 \
    libxshmfence1 \
    libglu1 \
    && rm -rf /var/lib/apt/lists/*

# Python deps
COPY requirements.txt .
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# ✅ Install Playwright browsers ONLY (no deps)
RUN playwright install chromium

# Copy project
COPY . .
EXPOSE 8123
CMD ["python", "run.py"]