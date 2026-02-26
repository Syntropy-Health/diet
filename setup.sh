#!/bin/bash

# Diet Insight Engine - Setup Script
# This script sets up the complete development environment

set -e

echo "🛠️  Diet Insight Engine - Setup"
echo "==============================="

# Check Python version
python_version=$(python3 --version 2>&1 | cut -d' ' -f2)
required_version="3.8"

if python3 -c "import sys; exit(0 if sys.version_info >= (3, 8) else 1)"; then
    echo "✅ Python $python_version is compatible"
else
    echo "❌ Python 3.8+ is required. Current version: $python_version"
    exit 1
fi

# Install UV if not present
if ! command -v uv &> /dev/null; then
    echo "📦 Installing UV package manager..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    source ~/.bashrc || source ~/.zshrc || true
    export PATH="$HOME/.cargo/bin:$PATH"
else
    echo "✅ UV package manager already installed"
fi

# Create virtual environment and install dependencies
echo "🔧 Setting up virtual environment and dependencies..."
uv sync

# Set up environment variables
if [ ! -f .env ]; then
    echo "📝 Setting up environment variables..."
    cp .env.template .env
    echo "✅ Created .env file from template"
else
    echo "✅ .env file already exists"
fi

# Make scripts executable
chmod +x quickstart.sh
chmod +x setup.sh
echo "✅ Made scripts executable"

# Create necessary directories
mkdir -p logs
mkdir -p output
echo "✅ Created necessary directories"

# Validate the setup
echo "🔍 Validating setup..."
if uv run python validate_setup.py; then
    echo ""
    echo "🎉 Setup completed successfully!"
    echo ""
    echo "Next steps:"
    echo "1. Edit the .env file and add your API keys:"
    echo "   • OPENAI_API_KEY (required for LLM functionality)"
    echo "   • LANGCHAIN_API_KEY (optional, for monitoring)"
    echo ""
    echo "2. Run the quickstart script:"
    echo "   ./quickstart.sh"
    echo ""
    echo "3. Or run directly:"
    echo "   python main.py --user-id your_user_id"
    echo ""
    echo "📚 For more information, read the README.md"
else
    echo ""
    echo "❌ Setup validation failed!"
    echo "Please check the errors above and fix them."
    echo "Common issues:"
    echo "• Missing API keys in .env file"
    echo "• Network connectivity issues"
    echo "• Python environment issues"
    echo ""
    echo "After fixing issues, run: python validate_setup.py"
fi
