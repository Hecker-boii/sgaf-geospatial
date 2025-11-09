#!/usr/bin/env bash
set -euo pipefail

echo "🚀 Setting up GitHub Repository for SGAF"
echo ""

# Check if git is initialized
if [ ! -d .git ]; then
    echo "❌ Git not initialized. Run 'git init' first."
    exit 1
fi

# Check current branch
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "master")
echo "📦 Current branch: $CURRENT_BRANCH"

# Rename to main if needed
if [ "$CURRENT_BRANCH" != "main" ]; then
    echo "🔄 Renaming branch to 'main'..."
    git branch -M main
    CURRENT_BRANCH="main"
fi

echo ""
echo "📋 Next Steps:"
echo ""
echo "1. Create a GitHub repository:"
echo "   - Go to: https://github.com/new"
echo "   - Repository name: sgaf-geospatial"
echo "   - Description: Serverless Geospatial Analysis Framework - 14+ AWS Services"
echo "   - Choose: Public"
echo "   - DO NOT initialize with README, .gitignore, or license"
echo "   - Click 'Create repository'"
echo ""
echo "2. After creating the repository, run:"
echo "   git remote add origin https://github.com/YOUR_USERNAME/sgaf-geospatial.git"
echo "   git push -u origin main"
echo ""
echo "   OR if you have GitHub CLI installed:"
echo "   gh repo create sgaf-geospatial --public --source=. --remote=origin --push"
echo ""
echo "3. Then connect to AWS Amplify:"
echo "   - Go to: https://console.aws.amazon.com/amplify/"
echo "   - Click 'New app' → 'Host web app'"
echo "   - Select 'GitHub' and authorize"
echo "   - Select repository: sgaf-geospatial"
echo "   - Select branch: main"
echo "   - Review build settings (amplify.yml will be auto-detected)"
echo "   - Click 'Save and deploy'"
echo ""
echo "✅ Your code is ready to push!"
echo ""

# Check if remote already exists
if git remote get-url origin &>/dev/null; then
    REMOTE_URL=$(git remote get-url origin)
    echo "📍 Current remote: $REMOTE_URL"
    echo ""
    echo "To push to GitHub, run:"
    echo "  git push -u origin main"
else
    echo "⚠️  No remote repository configured yet."
    echo "   Follow the steps above to create and connect your GitHub repository."
fi

