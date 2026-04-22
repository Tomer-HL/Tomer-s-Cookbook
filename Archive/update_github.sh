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

cd "$REPO_DIR" || { echo "❌  תיקייה לא נמצאה: $REPO_DIR"; exit 1; }

echo "🍳  מריץ generate_recipe.py..."
python3 generate_recipe.py

echo "📖  מריץ generate_index.py..."
python3 generate_index.py

echo "📦  מוסיף שינויים ל-git..."
git add .

# בדיקה אם יש שינויים לפני commit
if git diff --cached --quiet; then
    echo "ℹ️   אין שינויים חדשים — לא נדרש commit."
    exit 0
fi

echo "✏️   מבצע commit..."
git commit -m "$COMMIT_MSG – $(date '+%Y-%m-%d %H:%M')"

echo "📤  מעלה ל-GitHub..."
git push origin main

echo ""
echo "✅  הכל עודכן בהצלחה!"
echo "🌐  הסייט יהיה זמין בעוד כ-30 שניות ב-GitHub Pages."
