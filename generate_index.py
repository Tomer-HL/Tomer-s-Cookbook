"""
generate_index.py
-----------------
סורק את תיקיית cookbook/ ובונה index_en.html + index_he.html
מסודרים לפי קטגוריה עם עיצוב תואם למתכונים.

מבנה תיקיות צפוי:
  cookbook/
    entrees/RecipeName/RecipeName_en.html
    sides/RecipeName/RecipeName_en.html
    bread/RecipeName/RecipeName_en.html
    desserts/RecipeName/RecipeName_en.html
"""

from pathlib import Path
import re

# ============================================================
#  הגדרות
# ============================================================

COOKBOOK_DIR = Path("cookbook")

CATEGORIES_ORDER = ["entrees", "sides", "bread", "desserts"]

CATEGORY_META = {
    "entrees":  {"en": "Entrees",        "he": "עיקריות",       "icon": "🍳"},
    "sides":    {"en": "Sides",          "he": "תוספות",        "icon": "🥗"},
    "bread":    {"en": "Bread & Pastry", "he": "לחמים ומאפים",  "icon": "🍞"},
    "desserts": {"en": "Desserts",       "he": "קינוחים",       "icon": "🍮"},
}

SITE_TITLE_EN = "Tomer's Israeli Cookbook"
SITE_TITLE_HE = "ספר המתכונים הישראלי של תומר"
SITE_SUBTITLE_EN = "Traditional Israeli recipes from my kitchen to yours"
SITE_SUBTITLE_HE = "מתכונים ישראליים מסורתיים מהמטבח שלי למטבח שלכם"

# ============================================================


def extract_title_from_html(html_path: Path) -> str:
    """Extract title from HTML, fallback to folder name if not found."""
    try:
        text = html_path.read_text(encoding="utf-8")
        m = re.search(r"<h1[^>]*>(.*?)</h1>", text, re.IGNORECASE | re.DOTALL)
        if m:
            return re.sub(r"<[^>]+>", "", m.group(1)).strip()
        m = re.search(r"<title>(.*?)</title>", text, re.IGNORECASE)
        if m:
            return m.group(1).strip()
    except Exception:
        pass
    return html_path.parent.name


def find_hero_image(recipe_dir: Path) -> str | None:
    for ext in (".jpg", ".jpeg", ".png", ".webp"):
        candidates = list(recipe_dir.glob(f"*{ext}"))
        if candidates:
            return candidates[0].name
    return None


def scan_cookbook(lang: str) -> dict[str, list[dict]]:
    """
    Return: { category: [ {title, html_path, image_path}, ... ] }
    """
    result: dict[str, list[dict]] = {cat: [] for cat in CATEGORIES_ORDER}
    suffix = f"_{lang}.html"

    for cat in CATEGORIES_ORDER:
        cat_dir = COOKBOOK_DIR / cat
        if not cat_dir.exists():
            continue
        for recipe_dir in sorted(cat_dir.iterdir()):
            if not recipe_dir.is_dir():
                continue
            html_file = recipe_dir / f"{recipe_dir.name}{suffix}"
            if not html_file.exists():
                # נסה למצוא כל קובץ HTML עם הסיומת הנכונה
                candidates = list(recipe_dir.glob(f"*{suffix}"))
                if not candidates:
                    continue
                html_file = candidates[0]

            title      = extract_title_from_html(html_file)
            image_file = find_hero_image(recipe_dir)
            image_path = str(recipe_dir / image_file) if image_file else None
            # נתיב יחסי מ-cookbook/ לקובץ ה-HTML
            rel_path   = html_file.relative_to(COOKBOOK_DIR)

            result[cat].append({
                "title":      title,
                "html":       str(rel_path).replace("\\", "/"),
                "image":      str(Path(recipe_dir.relative_to(COOKBOOK_DIR) / image_file)).replace("\\", "/")
                              if image_file else None,
            })

    return result


def build_index(lang: str) -> str:
    is_he     = lang == "he"
    direction = "rtl" if is_he else "ltr"
    font      = "Alef, system-ui, sans-serif" if is_he else \
                "'Playfair Display', Georgia, serif"
    body_font = "Alef, system-ui, sans-serif" if is_he else \
                "'Lato', system-ui, sans-serif"

    title    = SITE_TITLE_HE    if is_he else SITE_TITLE_EN
    subtitle = SITE_SUBTITLE_HE if is_he else SITE_SUBTITLE_EN
    other    = "index_en.html"  if is_he else "index_he.html"
    switch   = '<img src="flag_gb.png" alt="EN"> English' if is_he else \
               '<img src="flag_il.png" alt="עב"> עברית'
    no_img   = "אין תמונה"      if is_he else "No image"

    data = scan_cookbook(lang)

    # בניית כרטיסיות לפי קטגוריות
    sections_html = ""
    for cat in CATEGORIES_ORDER:
        recipes = data.get(cat, [])
        if not recipes:
            continue
        meta      = CATEGORY_META[cat]
        cat_label = meta["he"] if is_he else meta["en"]
        icon      = meta["icon"]

        cards = ""
        for r in recipes:
            img_tag = (
                f'<img src="{r["image"]}" alt="{r["title"]}" loading="lazy">'
                if r["image"]
                else f'<div class="no-img">{no_img}</div>'
            )
            cards += f"""
            <a class="card" href="{r['html']}">
              <div class="card-img">{img_tag}</div>
              <div class="card-body">
                <span class="card-title">{r['title']}</span>
              </div>
            </a>"""

        sections_html += f"""
        <section class="category">
          <h2 class="cat-title"><span class="cat-icon">{icon}</span> {cat_label}</h2>
          <div class="cards">{cards}
          </div>
        </section>"""

    gfonts = (
        '<link href="https://fonts.googleapis.com/css2?family=Playfair+Display:wght@600;700&family=Lato:wght@400;600&display=swap" rel="stylesheet">'
        if not is_he else
        '<link href="https://fonts.googleapis.com/css2?family=Alef:wght@400;700&display=swap" rel="stylesheet">'
    )

    return f"""<!DOCTYPE html>
<html lang="{lang}" dir="{direction}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
{gfonts}
<style>
:root {{
    --orange: #d35400;
    --orange-light: #f39c12;
    --bg: #fdf8f0;
    --card-bg: #ffffff;
    --border: #f0e0d0;
    --text: #2c1a0e;
    --muted: #7a6a5a;
}}

* {{ box-sizing: border-box; margin: 0; padding: 0; }}

body {{
    font-family: {body_font};
    background-color: var(--bg);
    background-image:
        radial-gradient(ellipse at 20% 10%, rgba(211,84,0,0.06) 0%, transparent 60%),
        radial-gradient(ellipse at 80% 80%, rgba(243,156,18,0.07) 0%, transparent 60%);
    min-height: 100vh;
    color: var(--text);
}}

/* ---- Header ---- */
.site-header {{
    background: linear-gradient(135deg, #2c1a0e 0%, #5a3010 100%);
    padding: 48px 24px 40px;
    text-align: center;
    position: relative;
    overflow: hidden;
}}
.site-header::before {{
    content: "";
    position: absolute;
    inset: 0;
    background-image: repeating-linear-gradient(
        45deg,
        rgba(255,255,255,0.02) 0px,
        rgba(255,255,255,0.02) 1px,
        transparent 1px,
        transparent 12px
    );
}}
.lang-switch {{
    position: absolute;
    top: 16px;
    {"left" if is_he else "right"}: 20px;
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 13px;
    color: rgba(255,255,255,0.75);
    text-decoration: none;
    background: rgba(255,255,255,0.1);
    padding: 5px 10px;
    border-radius: 20px;
    transition: background 0.2s;
}}
.lang-switch:hover {{ background: rgba(255,255,255,0.2); color: #fff; }}
.lang-switch img {{ width: 20px; height: 14px; border-radius: 2px; }}

.site-title {{
    font-family: {font};
    font-size: clamp(28px, 5vw, 52px);
    color: #fff;
    letter-spacing: 0.02em;
    position: relative;
    line-height: 1.15;
}}
.title-accent {{
    color: var(--orange-light);
}}
.site-subtitle {{
    margin-top: 10px;
    font-size: clamp(13px, 2vw, 16px);
    color: rgba(255,255,255,0.6);
    position: relative;
    font-style: italic;
}}
.header-divider {{
    width: 60px;
    height: 3px;
    background: var(--orange-light);
    margin: 18px auto 0;
    border-radius: 2px;
    position: relative;
}}

/* ---- Main ---- */
main {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 48px 24px 64px;
}}

/* ---- Category sections ---- */
.category {{
    margin-bottom: 52px;
}}
.cat-title {{
    font-family: {font};
    font-size: 22px;
    color: var(--orange);
    margin-bottom: 20px;
    display: flex;
    align-items: center;
    gap: 10px;
    border-bottom: 2px solid var(--border);
    padding-bottom: 10px;
}}
.cat-icon {{ font-size: 26px; }}

/* ---- Cards grid ---- */
.cards {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
    gap: 20px;
}}
.card {{
    background: var(--card-bg);
    border-radius: 14px;
    overflow: hidden;
    text-decoration: none;
    color: var(--text);
    box-shadow: 0 3px 12px rgba(0,0,0,0.07);
    border: 1px solid var(--border);
    transition: transform 0.18s ease, box-shadow 0.18s ease;
    display: flex;
    flex-direction: column;
}}
.card:hover {{
    transform: translateY(-4px);
    box-shadow: 0 10px 28px rgba(211,84,0,0.15);
}}
.card-img {{
    height: 155px;
    overflow: hidden;
    background: #f5ebe0;
}}
.card-img img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.35s ease;
}}
.card:hover .card-img img {{
    transform: scale(1.05);
}}
.no-img {{
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--muted);
    font-size: 13px;
    background: linear-gradient(135deg, #f5ebe0, #fdf3e8);
}}
.card-body {{
    padding: 14px 16px 16px;
    flex: 1;
    display: flex;
    align-items: center;
}}
.card-title {{
    font-size: 15px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.35;
}}

/* ---- Footer ---- */
footer {{
    text-align: center;
    padding: 24px;
    font-size: 13px;
    color: var(--muted);
    border-top: 1px solid var(--border);
}}

@media (max-width: 480px) {{
    .cards {{ grid-template-columns: repeat(2, 1fr); gap: 12px; }}
    .card-img {{ height: 120px; }}
}}
</style>
</head>
<body>

<header class="site-header">
  <a class="lang-switch" href="{other}">{switch}</a>
  <h1 class="site-title">
    {'<span class="title-accent">ספר המתכונים</span><br>הישראלי של תומר' if is_he else
     'Tomer\'s <span class="title-accent">Israeli</span> Cookbook'}
  </h1>
  <p class="site-subtitle">{subtitle}</p>
  <div class="header-divider"></div>
</header>

<main>
  {sections_html}
</main>

<footer>
  © 2020 Tomer Hillel · All rights reserved
</footer>

</body>
</html>
"""


def main() -> None:
    COOKBOOK_DIR.mkdir(exist_ok=True)

    for lang in ("en", "he"):
        out = Path(f"cookbook/index_{lang}.html")
        out.write_text(build_index(lang), encoding="utf-8")
        print(f"✅  created: cookbook/index_{lang}.html")

    print("\n📖 open the cookbook/index_en.html In the browser to see the index.")


if __name__ == "__main__":
    main()
