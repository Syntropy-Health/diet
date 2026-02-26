#!/bin/bash

# Diet Insight Engine - Quick Start Script
# This script helps you get started with the DIE pipeline quickly

set -e

echo "🚀 Diet Insight Engine - Quick Start"
echo "===================================="

# Check if UV is installed
if ! command -v uv &> /dev/null; then
    echo "❌ UV package manager not found. Please install UV first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

echo "✅ UV package manager found"

# Install dependencies
echo "📦 Installing dependencies..."
uv sync

# Check if .env file exists
if [ ! -f .env ]; then
    echo "📝 Creating .env file from template..."
    cp .env.template .env
    echo "⚠️  Please edit .env file with your API keys before continuing"
    echo "   At minimum, set your OPENAI_API_KEY"

    # Ask if user wants to edit now
    read -p "Do you want to edit .env now? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        ${EDITOR:-nano} .env
    fi
else
    echo "✅ .env file already exists"
fi

# Validate setup
echo "🔍 Validating setup..."
if python validate_setup.py; then
    echo "✅ Setup validation passed!"
else
    echo "❌ Setup validation failed. Please check the errors above."
    exit 1
fi

# Ask what to run
echo ""
echo "🎯 What would you like to do?"
echo "1. Run full pipeline with sample data"
echo "2. Run symptom analysis only"
echo "3. Run nutritional recommendations only"
echo "4. Exit"

read -p "Enter your choice (1-4): " -n 1 -r
echo

case $REPLY in
    1)
        echo "🏃 Running full DIE pipeline with sample data..."
        python main.py --user-id quickstart_user
        ;;
    2)
        echo "🏃 Running symptom analysis module..."
        python main.py --module symptom-analysis --user-id quickstart_user
        ;;
    3)
        echo "ℹ️  For nutritional recommendations, you need a symptom analysis file."
        echo "   Run option 1 or 2 first to generate analysis results."
        ;;
    4)
        echo "👋 Goodbye!"
        exit 0
        ;;
    *)
        echo "❌ Invalid option. Please run the script again."
        exit 1
        ;;
esac

echo ""
echo "🎉 Quick start completed!"
echo ""
echo "Next steps:"
echo "• Check the output above for results"
echo "• Try with your own journal data using --input-file"
echo "• Read the README.md for more detailed usage instructions"
