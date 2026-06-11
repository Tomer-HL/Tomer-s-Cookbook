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
                "html":       "/cookbook/" + str(rel_path).replace("\\", "/"),
                "image":      "/cookbook/" + str(Path(recipe_dir.relative_to(COOKBOOK_DIR) / image_file)).replace("\\", "/")
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
    other    = "/cookbook/" if is_he else "/cookbook/index_he.html"
    switch   = '<img src="/cookbook/flag_gb.png" alt="EN"> English' if is_he else \
               '<img src="/cookbook/flag_il.png" alt="עב"> עברית'
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
        count     = len(recipes)
        count_lbl = f"{count} מתכונים" if is_he else f"{count} recipe{'s' if count != 1 else ''}"

        cards = ""
        for r in recipes:
            img_tag = (
                f'<img src="{r["image"]}" alt="{r["title"]}" loading="lazy">'
                if r["image"]
                else f'<div class="no-img">{no_img}</div>'
            )
            cards += f"""
            <a class="card" href="{r['html']}">
              <div class="card-img">{img_tag}<span class="card-chip">{icon} {cat_label}</span></div>
              <div class="card-body">
                <span class="card-title">{r['title']}</span>
              </div>
            </a>"""

        sections_html += f"""
        <section class="category">
          <h2 class="cat-title"><span class="cat-chip">{icon}</span> {cat_label}<span class="cat-count">{count_lbl}</span></h2>
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
    --gold: #c8923d;
    --bg: #fdf8f0;
    --card-bg: #ffffff;
    --border: #efe2d2;
    --text: #2c1a0e;
    --muted: #8a7561;
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
    border-top: 3px solid var(--gold);
    padding: 44px 24px 38px;
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

.site-overline {{
    position: relative;
    font-family: {body_font};
    font-size: 12px;
    letter-spacing: 0.32em;
    text-transform: uppercase;
    color: #e0a84e;
    margin-bottom: 10px;
}}
.site-title {{
    font-family: {font};
    font-size: clamp(30px, 5vw, 50px);
    color: #fff;
    letter-spacing: 0.01em;
    position: relative;
    line-height: 1.12;
}}
.title-accent {{
    color: var(--orange-light);
}}
.site-subtitle {{
    margin-top: 12px;
    font-size: clamp(13px, 2vw, 16px);
    color: rgba(255,255,255,0.62);
    position: relative;
    font-style: italic;
}}
.header-divider {{
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 9px;
    margin: 18px auto 0;
    position: relative;
}}
.header-divider .line {{
    width: 34px;
    height: 2px;
    background: var(--gold);
    border-radius: 2px;
}}
.header-divider .diamond {{
    width: 7px;
    height: 7px;
    background: var(--orange-light);
    transform: rotate(45deg);
}}

/* ---- Main ---- */
main {{
    max-width: 1100px;
    margin: 0 auto;
    padding: 48px 24px 64px;
}}

/* ---- Category sections ---- */
.category {{
    margin-bottom: 50px;
}}
.cat-title {{
    font-family: {font};
    font-size: 23px;
    font-weight: 600;
    color: var(--orange);
    margin-bottom: 22px;
    display: flex;
    align-items: center;
    gap: 11px;
    border-bottom: 2px solid var(--border);
    padding-bottom: 11px;
}}
.cat-chip {{
    width: 40px;
    height: 40px;
    border-radius: 12px;
    background: #fbeede;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 21px;
    flex-shrink: 0;
}}
.cat-count {{
    font-size: 13px;
    font-weight: 600;
    color: #a08a74;
    {"margin-right" if is_he else "margin-left"}: 4px;
}}

/* ---- Cards grid ---- */
.cards {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(210px, 1fr));
    gap: 22px;
}}
.card {{
    background: var(--card-bg);
    border-radius: 16px;
    overflow: hidden;
    text-decoration: none;
    color: var(--text);
    box-shadow: 0 2px 10px rgba(120,70,20,0.06);
    border: 1px solid var(--border);
    transition: transform 0.2s ease, box-shadow 0.2s ease;
    display: flex;
    flex-direction: column;
}}
.card:hover {{
    transform: translateY(-5px);
    box-shadow: 0 14px 30px rgba(211,84,0,0.16);
}}
.card-img {{
    height: 155px;
    position: relative;
    overflow: hidden;
    background: #f5ebe0;
}}
.card-img img {{
    width: 100%;
    height: 100%;
    object-fit: cover;
    transition: transform 0.4s ease;
}}
.card:hover .card-img img {{
    transform: scale(1.06);
}}
.card-chip {{
    position: absolute;
    top: 10px;
    {"right" if is_he else "left"}: 10px;
    background: rgba(255,255,255,0.92);
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.03em;
    color: #a9521a;
    padding: 4px 10px;
    border-radius: 20px;
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
    padding: 14px 16px 17px;
    flex: 1;
    display: flex;
    align-items: center;
}}
.card-title {{
    font-family: {font};
    font-size: 18px;
    font-weight: 600;
    color: var(--text);
    line-height: 1.25;
    transition: color 0.2s;
}}
.card:hover .card-title {{
    color: var(--orange);
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
    .cards {{ grid-template-columns: repeat(2, 1fr); gap: 14px; }}
    .card-img {{ height: 124px; }}
    .card-title {{ font-size: 16px; }}
}}
</style>
</head>
<body>

<header class="site-header">
  <a class="lang-switch" href="{other}">{switch}</a>
  <p class="site-overline">{'מהמטבח הביתי הישראלי' if is_he else 'Israeli home cooking'}</p>
  <h1 class="site-title">
    {'<span class="title-accent">ספר המתכונים</span><br>הישראלי של תומר' if is_he else
     'Tomer\'s <span class="title-accent">Israeli</span> Cookbook'}
  </h1>
  <p class="site-subtitle">{subtitle}</p>
  <div class="header-divider"><span class="line"></span><span class="diamond"></span><span class="line"></span></div>
</header>

<main>
  {sections_html}
</main>

<footer>
  © 2020 Tomer Hillel · All rights reserved
</footer>

<!-- Floating edit button — links to the password-protected editor -->
<a class="edit-fab" href="/admin" title="Edit recipes">✏️</a>
<style>
.edit-fab {{
    position: fixed;
    bottom: 28px;
    right: 28px;
    width: 52px;
    height: 52px;
    background: linear-gradient(135deg, #d35400 0%, #b94600 100%);
    color: #fff;
    font-size: 22px;
    line-height: 52px;
    text-align: center;
    border-radius: 50%;
    text-decoration: none;
    box-shadow: 0 4px 16px rgba(211,84,0,0.35);
    transition: transform 0.15s, box-shadow 0.15s;
    z-index: 999;
}}
.edit-fab:hover {{
    transform: scale(1.1);
    box-shadow: 0 6px 20px rgba(211,84,0,0.5);
}}
</style>

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
