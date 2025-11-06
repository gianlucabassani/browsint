#!/bin/bash

# Browsint Web Interface Build Script

echo "🚀 Building Browsint Web Interface..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "❌ Node.js is not installed. Please install Node.js 18+ first."
    exit 1
fi

# Check if npm is installed
if ! command -v npm &> /dev/null; then
    echo "❌ npm is not installed. Please install npm first."
    exit 1
fi

# Check Node.js version
NODE_VERSION=$(node -v | cut -d'v' -f2 | cut -d'.' -f1)
if [ "$NODE_VERSION" -lt 18 ]; then
    echo "❌ Node.js version 18+ is required. Current version: $(node -v)"
    exit 1
fi

echo "✅ Node.js version: $(node -v)"
echo "✅ npm version: $(npm -v)"

# Install dependencies
echo "📦 Installing dependencies..."
npm install

if [ $? -ne 0 ]; then
    echo "❌ Failed to install dependencies"
    exit 1
fi

# Build the React app
echo "🔨 Building React app..."
npm run build

if [ $? -ne 0 ]; then
    echo "❌ Failed to build React app"
    exit 1
fi

echo "✅ Build completed successfully!"
echo "📁 Built files are in the 'dist/' directory"
echo ""
echo "🚀 To start the web interface:"
echo "   python app.py"
echo ""
echo "🌐 The interface will be available at: http://localhost:8000" 