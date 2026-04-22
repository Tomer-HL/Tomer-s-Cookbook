import re
from pathlib import Path

# ============================================================
#  ⚙️  הגדרות המתכון — שנה רק כאן
# ============================================================

RECIPE_NAME   = "Baked_Cheesecake"         # שם קובץ (ללא סיומת)
CATEGORY      = "desserts"          # entrees | sides | bread | desserts
TIME_EN       = "1:45 hours"
TIME_HE       = "1:45 שעות"
LEVEL_EN      = "Medium"             # Easy | Medium | Hard
LEVEL_HE      = "בינוני"               # קל | בינוני | מאתגר
SERVINGS      = 8

# Entrees / עיקריות
# Israeli Crispy Schnitzel
# Israeli Shakshuka
# Yemenite Chicken Soup
# Yemenite Beef Soup
# Lebanese/Syrian Arayes
# Turkish Kabab
# Moroccan Fish
# 🥗 Sides / תוספות
# Creamy Mushroom-Potato Gratin
# Potato Salad with Mayonnaise
# Schug
# Moroccan Matbucha
# Roasted Eggplant Salad / Baba Ganoush
# Hummus
# 🍞 Bread & Pastry / לחמים ומאפים
# Challah
# Yemenite Kubaniyot
# Cheese Bourekas
# Meat Bourekas
# 🍮 Desserts / קינוחים
# Israeli Biscuit Cake
# Yemenite Zalabyot
# Israeli Baked Cheesecake
# Israeli Chocolate Balls
# Chocolate Rugelach
# Rolled Cookies (Dates/Chocolate)
# Cheese Blintzes with Berry Sauce

# ============================================================
#  סוף הגדרות — אל תשנה מתחת לכאן
# ============================================================

VALID_CATEGORIES = {
    "entrees":  {"en": "Entrees",         "he": "עיקריות"},
    "sides":    {"en": "Sides",           "he": "תוספות"},
    "bread":    {"en": "Bread & Pastry",  "he": "לחמים ומאפים"},
    "desserts": {"en": "Desserts",        "he": "קינוחים"},
}


# ---------- Parsing helpers ---------------------------------

def extract_block(text: str, start_headers: list[str], stop_headers: list[str]) -> str:
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    start_set = set(start_headers)
    stop_set   = set(stop_headers)
    collecting = False
    collected: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped in start_set:
            collecting = True
            continue
        if collecting and stripped in stop_set:
            break
        if collecting:
            collected.append(line)
    return "\n".join(collected).strip()


def parse_list(block: str) -> list[str]:
    return [
        line.strip("•\t- ").strip()
        for line in block.splitlines()
        if line.strip("•\t- ").strip()
    ]


def parse_steps(block: str) -> list[str]:
    text = block.replace("\r\n", "\n").replace("\r", "\n")
    raw  = re.split(r"\n\s*\n|\n(?=\d+[\.\)]|\bStep\s+\d)", text)
    steps = []
    for s in raw:
        s = re.sub(r"^\s*(?:\d+[\.\)]|Step\s+\d+[:\.]?)\s*", "", s).strip()
        if s:
            steps.append(s)
    return steps


def parse_recipe_file(path: str) -> tuple[str, list[str], list[str], str]:
    text  = Path(path).read_text(encoding="utf-8")
    title = text.splitlines()[0].strip()
    all_h = ["Ingredients", "Instructions", "Description",
             "מצרכים", "אופן ההכנה", "תיאור"]
    return (
        title,
        parse_list(extract_block(text, ["Ingredients", "מצרכים"], all_h)),
        parse_steps(extract_block(text, ["Instructions", "אופן ההכנה"], all_h)),
        extract_block(text, ["Description", "תיאור"], all_h).strip(),
    )


# ---------- Shared CSS helpers ------------------------------

def _shared_list_css(is_he: bool) -> str:
    s = "right" if is_he else "left"
    return f"""
ul {{
    list-style: none;
    padding-{s}: 28px;
    margin: 0;
}}
ul li {{
    position: relative;
    padding-{s}: 28px;
    margin-bottom: 6px;
}}
ul li::before {{
    content: "❖";
    color: var(--orange);
    position: absolute;
    {s}: 0;
}}
ol {{
    list-style: none;
    counter-reset: step-counter;
    padding-{s}: 0;
    margin: 0;
}}
ol li {{
    counter-increment: step-counter;
    position: relative;
    margin-bottom: 14px;
    padding-{s}: 36px;
    font-size: 15px;
}}
ol li::before {{
    content: counter(step-counter);
    position: absolute;
    top: 0;
    {s}: 0;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: var(--orange);
    color: #fff;
    text-align: center;
    line-height: 28px;
    font-weight: bold;
}}"""


def _render_ingredients(ingredients: list[str]) -> str:
    return "".join(f"<li>{i}</li>" for i in ingredients)


def _render_steps(steps: list[str]) -> str:
    return "".join(f"<li>{s}</li>" for s in steps)


# ---------- Full HTML ---------------------------------------

def build_html(
    title: str,
    ingredients: list[str],
    instructions: list[str],
    description: str,
    *,
    lang: str       = "en",
    time_text: str  = "40 minutes",
    level_text: str = "Easy",
    servings: int   = 4,
    hero_image: str | None = None,
    file_other: str = "#",
    back_path: str  = "../../",
) -> str:
    is_he     = lang == "he"
    direction = "rtl" if is_he else "ltr"
    font      = "Alef, system-ui, sans-serif" if is_he else \
                "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

    index_lang = "he" if is_he else "en"
    back_file  = f"{back_path}index_{index_lang}.html"

    L = {
        "tag":          "מתכון"           if is_he else "RECIPE",
        "time":         "זמן"             if is_he else "Time",
        "servings":     "מנות"            if is_he else "Servings",
        "level":        "רמת קושי"        if is_he else "Level",
        "ingredients":  "מצרכים"          if is_he else "Ingredients",
        "instructions": "הוראות הכנה"     if is_he else "Instructions",
        "subtitle":     "מנה קלאסית שקל להכין בבית." if is_he else
                        "A classic dish you can easily make at home.",
        "print":        "הדפסה"           if is_he else "Print",
        "back":         "→ חזרה לאינדקס"  if is_he else "← Back to Index",
        "switch_link":  '<img src="../../flag_gb.png" alt="English"> English' if is_he else
                        '<img src="../../flag_il.png" alt="עברית"> עברית',
    }

    hero_tag = f'<img class="hero" src="{hero_image}" alt="{title}">' if hero_image else ""
    list_css = _shared_list_css(is_he)

    return f"""<!DOCTYPE html>
<html lang="{lang}" dir="{direction}">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
:root {{
    --orange: #d35400;
    --section-bg: #fffaf0;
    --border: #f7d8c5;
}}
body {{
    font-family: {font};
    background: linear-gradient(180deg, #fdf8f0 0%, #fffefc 100%);
    margin: 0;
    padding: 40px 16px;
    display: flex;
    justify-content: center;
}}
.page {{
    max-width: 900px;
    width: 100%;
    background: #ffffff;
    border-radius: 16px;
    box-shadow: 0 10px 30px rgba(0,0,0,0.08);
    padding: 28px 32px 32px;
    position: relative;
}}
.hero {{
    width: 100%;
    height: 260px;
    object-fit: cover;
    border-radius: 14px;
    margin: 20px 0 24px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.12);
}}
.top-bar {{
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    flex-wrap: wrap;
    gap: 8px;
}}
.back-link {{
    font-size: 14px;
    color: var(--orange);
    text-decoration: none;
    font-weight: 600;
}}
.back-link:hover {{ text-decoration: underline; }}
.top-right {{
    display: flex;
    gap: 12px;
    align-items: center;
}}
.lang-switch {{
    font-size: 14px;
    display: flex;
    align-items: center;
    gap: 4px;
    text-decoration: none;
    color: inherit;
}}
.lang-switch img {{ width: 20px; height: 14px; }}
.print-button {{
    padding: 4px 10px;
    font-size: 13px;
    border: none;
    border-radius: 5px;
    background: var(--orange);
    color: white;
    cursor: pointer;
}}
.print-button:hover {{ background: #e67e22; }}
.header-bar {{
    height: 3px;
    background: var(--orange);
    border-radius: 2px;
    margin-bottom: 18px;
}}
.tag {{
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 12px;
    color: #7a7a7a;
}}
h1 {{ margin: 6px 0; font-size: 32px; color: var(--orange); }}
.subtitle    {{ font-size: 15px; color: #666; margin-bottom: 6px; }}
.description {{ font-size: 15px; color: #444; }}
.meta {{
    display: flex;
    gap: 24px;
    flex-wrap: wrap;
    margin-top: 16px;
}}
.meta-item {{
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: 17px;
    color: #23412f;
}}
.meta-item .icon {{ font-size: 28px; }}
h2 {{ font-size: 20px; margin-bottom: 10px; color: var(--orange); }}
.section-box {{
    background: var(--section-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 16px;
}}
.divider {{
    height: 2px;
    background: linear-gradient(to right, var(--orange) 10%, #fff 50%, var(--orange) 90%);
    border: none;
    margin: 20px 0;
}}
{list_css}
</style>
</head>
<body>
<div class="page">
  <div class="top-bar">
    <a class="back-link" href="{back_file}">{L['back']}</a>
    <div class="top-right">
      <a class="lang-switch" href="{file_other}">{L['switch_link']}</a>
      <button class="print-button" onclick="window.print()">🖨️ {L['print']}</button>
    </div>
  </div>

  {hero_tag}
  <div class="header-bar"></div>

  <div class="header">
    <div class="tag">{L['tag']}</div>
    <h1>{title}</h1>
    <div class="subtitle">{L['subtitle']}</div>
    <div class="description">{description}</div>
    <div class="meta">
      <div class="meta-item"><span class="icon">🕒</span> <b>{L['time']}:</b> {time_text}</div>
      <div class="meta-item"><span class="icon">🍽️</span> <b>{L['servings']}:</b> {servings}</div>
      <div class="meta-item"><span class="icon">🧑‍🍳</span> <b>{L['level']}:</b> {level_text}</div>
    </div>
  </div>

  <div class="section-box">
    <h2>{L['ingredients']}</h2>
    <ul>{_render_ingredients(ingredients)}</ul>
  </div>
  <div class="divider"></div>
  <div class="section-box">
    <h2>{L['instructions']}</h2>
    <ol>{_render_steps(instructions)}</ol>
  </div>
</div>
</body>
</html>
"""


# ---------- Print HTML --------------------------------------

def build_print(
    title: str,
    ingredients: list[str],
    instructions: list[str],
    description: str,
    *,
    lang: str = "en",
) -> str:
    is_he     = lang == "he"
    direction = "rtl" if is_he else "ltr"
    L = {
        "ingredients":  "מצרכים"      if is_he else "Ingredients",
        "instructions": "הוראות הכנה" if is_he else "Instructions",
        "print":        "הדפסה"       if is_he else "Print",
    }
    list_css = _shared_list_css(is_he)
    return f"""<!DOCTYPE html>
<html lang="{lang}" dir="{direction}">
<head>
<meta charset="UTF-8">
<title>{title} – Print</title>
<style>
:root {{ --orange: #d35400; --section-bg: #fffaf0; --border: #f7d8c5; }}
body {{ font-family: Georgia, serif; padding: 40px; max-width: 800px;
        margin: auto; line-height: 1.5; background: #fff; }}
h1  {{ font-size: 32px; margin-bottom: 10px; color: var(--orange); }}
h2  {{ margin-top: 28px; border-bottom: 2px solid var(--orange);
       padding-bottom: 4px; color: var(--orange); }}
.section-box {{ background: var(--section-bg); border: 1px solid var(--border);
                border-radius: 10px; padding: 16px; margin-bottom: 16px; }}
.divider {{ border-top: 1px dashed var(--orange); margin: 20px 0; }}
.print-button {{ display: inline-block; margin-bottom: 20px; padding: 8px 12px;
                 font-size: 14px; border: none; border-radius: 6px;
                 background: var(--orange); color: white; cursor: pointer; }}
.print-button:hover {{ background: #e67e22; }}
{list_css}
</style>
</head>
<body>
  <h1>{title}</h1>
  <p>{description}</p>
  <button class="print-button" onclick="window.print()">🖨️ {L['print']}</button>
  <div class="section-box">
    <h2>{L['ingredients']}</h2>
    <ul>{_render_ingredients(ingredients)}</ul>
  </div>
  <div class="divider"></div>
  <div class="section-box">
    <h2>{L['instructions']}</h2>
    <ol>{_render_steps(instructions)}</ol>
  </div>
</body>
</html>
"""


# ---------- Main --------------------------------------------

def main() -> None:
    if CATEGORY not in VALID_CATEGORIES:
        print(f"❌  קטגוריה לא תקינה: '{CATEGORY}'. אפשרויות: {list(VALID_CATEGORIES)}")
        return

    # תיקיית הפלט: cookbook/<category>/<RecipeName>/
    out_dir = Path("cookbook") / CATEGORY / RECIPE_NAME
    out_dir.mkdir(parents=True, exist_ok=True)

    # חיפוש קובצי טקסט
    def find_txt(suffix: str) -> Path | None:
        for loc in [Path("."), out_dir]:
            p = loc / f"{RECIPE_NAME}_{suffix}.txt"
            if p.exists():
                return p
        return None

    txt_en = find_txt("en")
    txt_he = find_txt("he")
    if not txt_en:
        print(f"❌  {RECIPE_NAME}_en.txt not found.")
        return
    if not txt_he:
        print(f"❌  {RECIPE_NAME}_he.txt not found.")
        return

    # העתקת קבצי טקסט לתיקיית המתכון
    for src in [txt_en, txt_he]:
        dest = out_dir / src.name
        if src.resolve() != dest.resolve():
            dest.write_bytes(src.read_bytes())

    # חיפוש תמונה
    image_file = None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        for loc in [Path("."), out_dir]:
            p = loc / f"{RECIPE_NAME}{ext}"
            if p.exists():
                dest = out_dir / p.name
                if p.resolve() != dest.resolve():
                    dest.write_bytes(p.read_bytes())
                image_file = p.name
                break
        if image_file:
            break
    if not image_file:
        print(f"⚠️  No image found for '{RECIPE_NAME}' — Will be created without an image.")

    file_en   = f"{RECIPE_NAME}_en.html"
    file_he   = f"{RECIPE_NAME}_he.html"

    # English
    t, ing, inst, desc = parse_recipe_file(str(txt_en))
    (out_dir / file_en).write_text(
        build_html(t, ing, inst, desc,
                   lang="en", time_text=TIME_EN, level_text=LEVEL_EN,
                   servings=SERVINGS, hero_image=image_file,
                   file_other=file_he),
        encoding="utf-8",
    )
    (out_dir / f"{RECIPE_NAME}_en_print.html").write_text(
        build_print(t, ing, inst, desc, lang="en"), encoding="utf-8"
    )

    # Hebrew
    t, ing, inst, desc = parse_recipe_file(str(txt_he))
    (out_dir / file_he).write_text(
        build_html(t, ing, inst, desc,
                   lang="he", time_text=TIME_HE, level_text=LEVEL_HE,
                   servings=SERVINGS, hero_image=image_file,
                   file_other=file_en),
        encoding="utf-8",
    )
    (out_dir / f"{RECIPE_NAME}_he_print.html").write_text(
        build_print(t, ing, inst, desc, lang="he"), encoding="utf-8"
    )

    print(f"✅  4 files were created in the folder: cookbook/{CATEGORY}/{RECIPE_NAME}/")
    print(f"   Run the generate_index.py To update the index.")
    
# מחיקת קבצי המקור מהתיקייה הראשית אחרי העברה לתיקיית המתכון
    print("🧹  Cleans source files from the main folder...")
    files_to_clean = [
        Path(f"{RECIPE_NAME}_en.txt"),
        Path(f"{RECIPE_NAME}_he.txt"),
    ]
    # מחיקת תמונה מהתיקייה הראשית אם הועתקה
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = Path(f"{RECIPE_NAME}{ext}")
        if p.exists():
            files_to_clean.append(p)

    for f in files_to_clean:
        if f.exists() and f.resolve() != (out_dir / f.name).resolve():
            f.unlink()
            print(f"   🗑️  Deleted: {f.name}")

if __name__ == "__main__":
    main()