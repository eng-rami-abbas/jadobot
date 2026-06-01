# Use Python 3.11 slim image
FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    RAILWAY_ENVIRONMENT=production

# Install system dependencies required for Playwright Firefox
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libxkbcommon0 \
    libxcomposite1 \
    libxdamage1 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    libatspi2.0-0 \
    libwayland-client0 \
    libdbus-glib-1-2 \
    libgtk-3-0 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security FIRST
RUN useradd --create-home --shell /bin/bash app

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Verify playwright-stealth is installed
RUN python -c "from playwright_stealth import stealth_async; print('playwright-stealth OK')" || \
    pip install playwright-stealth

# Install Playwright Firefox browser with system dependencies AS the app user
USER app
RUN playwright install firefox --with-deps
USER root

# Copy application code
COPY . .

# Fix ownership
RUN chown -R app:app /app

# Switch to app user
USER app

# Expose port for Railway
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Start the bot
CMD ["python", "bot.py"]
