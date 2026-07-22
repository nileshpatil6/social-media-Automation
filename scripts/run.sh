#!/bin/bash

echo "🚀 Starting Instagram Posting Agent..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📥 Installing dependencies..."
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Please copy .env.example to .env and configure your credentials."
    cp .env.example .env
    echo "📝 .env file created. Please edit it with your credentials before running the app."
    exit 1
fi

# Start the application
echo "🌟 Starting the application..."
python app.py