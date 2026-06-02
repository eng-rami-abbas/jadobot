#!/bin/bash

# iChancy Bot Deployment Script
echo "🚀 Starting iChancy Bot Deployment..."

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "❌ Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    echo "❌ Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
echo "📁 Creating directories..."
mkdir -p logs backups nginx/ssl

# Set permissions
echo "🔒 Setting permissions..."
chmod +x deployment/start.sh
chmod 755 logs backups

# Check if .env file exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Creating template..."
    cat > .env << EOF
# Bot Configuration
BOT_TOKEN=YOUR_BOT_TOKEN_HERE
COOKIE_STRING=YOUR_COOKIE_STRING_HERE
ADMIN_TELEGRAM_ID=YOUR_ADMIN_ID_HERE
MONGO_URI=YOUR_MONGO_URI_HERE

# Admin Panel Configuration
SECRET_KEY=your-secret-key-here-change-in-production

# Database Configuration
DB_PATH=./database.db

# Logging
LOG_LEVEL=INFO
EOF
    echo "📝 Please edit .env file with your actual configuration values."
    exit 1
fi

# Build and start services
echo "🔨 Building Docker images..."
docker-compose -f deployment/docker-compose.yml build

echo "🚀 Starting services..."
docker-compose -f deployment/docker-compose.yml up -d

# Wait for services to start
echo "⏳ Waiting for services to start..."
sleep 10

# Check service status
echo "📊 Checking service status..."
docker-compose -f deployment/docker-compose.yml ps

# Show logs
echo "📋 Showing recent logs..."
echo "Bot logs:"
docker-compose -f deployment/docker-compose.yml logs --tail=20 bot

echo "Admin panel logs:"
docker-compose -f deployment/docker-compose.yml logs --tail=20 admin_panel

echo "✅ Deployment complete!"
echo "🌐 Admin panel should be available at: http://localhost:8080"
echo "🔑 Default admin credentials: admin / admin123"
echo "📊 To view logs: docker-compose -f deployment/docker-compose.yml logs -f"
echo "🛑 To stop: docker-compose -f deployment/docker-compose.yml down"
