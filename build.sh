#!/bin/bash
# Build script for Render deployment

echo "🚀 Starting Render build..."

# Install dependencies
echo "📦 Installing dependencies..."
pip install -r requirements.txt

# Run database migrations
echo "🗄️  Running database migrations..."
python manage.py migrate --noinput

# Populate questions (only if database is empty)
echo "📝 Populating initial data..."
python manage.py populate_questions

# Collect static files
echo "📁 Collecting static files..."
python manage.py collectstatic --noinput --clear

echo "✅ Build complete!"
