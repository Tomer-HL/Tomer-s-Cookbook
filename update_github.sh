#!/bin/bash

# ============================================================
#  ⚙️  הגדרות — שנה רק כאן
# ============================================================
REPO_DIR="$HOME/projects/recipes"
COMMIT_MSG="Update recipes"

# ============================================================
#  סוף הגדרות
# ============================================================

set -e   # עצור אם יש שגיאה

cd "$REPO_DIR" || { echo "❌  Folder did not found: $REPO_DIR"; exit 1; }

echo "🍳  Runing generate_recipe.py..."
python3 generate_recipe.py

echo "📖  Runing generate_index.py..."
python3 generate_index.py

echo "📦  Adding the changes to git..."
git add .

# בדיקה אם יש שינויים לפני commit
if git diff --cached --quiet; then
    echo "ℹ️   No new changes - no need to commit."
    exit 0
fi

echo "✏️   execute commit..."
git commit -m "$COMMIT_MSG – $(date '+%Y-%m-%d %H:%M')"

echo "📤  Upload to -GitHub..."
git push origin main

echo ""
echo "✅  Successfully updated!"
echo "🌐  The website will be ready in 30 sec at -GitHub Pages."
