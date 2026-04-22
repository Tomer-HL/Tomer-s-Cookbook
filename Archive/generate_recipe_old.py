import re
from pathlib import Path

# ============================================================
#  ⚙️  הגדרות המתכון — שנה רק כאן
# ============================================================

RECIPE_NAME   = "Arayes"      # שם קובץ (ללא סיומת) — חייב להתאים לקבצי ה-.txt
TIME_EN       = "50 minutes"
TIME_HE       = "50 דקות"
LEVEL_EN      = "Medium"           # Easy / Medium / Hard
LEVEL_HE      = "בינוני"             # קל / בינוני / מאתגר
SERVINGS      = 4                # מספר מנות

# ============================================================
#  סוף הגדרות — אל תשנה מתחת לכאן
# ============================================================


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
    # תמיכה גם בשורה ריקה וגם בצעדים ממוספרים (1. / 1) / Step 1)
    raw = re.split(r"\n\s*\n|\n(?=\d+[\.\)]|\bStep\s+\d)", text)
    # ניקוי מספור אם קיים
    steps = []
    for s in raw:
        s = re.sub(r"^\s*(?:\d+[\.\)]|Step\s+\d+[:\.]?)\s*", "", s).strip()
        if s:
            steps.append(s)
    return steps


def parse_recipe_file(path: str) -> tuple[str, list[str], list[str], str]:
    text = Path(path).read_text(encoding="utf-8")
    title = text.splitlines()[0].strip()

    all_headers_en = ["Ingredients", "Instructions", "Description"]
    all_headers_he = ["מצרכים", "אופן ההכנה", "תיאור"]
    all_headers    = all_headers_en + all_headers_he

    ingredients_block  = extract_block(text, ["Ingredients", "מצרכים"],           all_headers)
    instructions_block = extract_block(text, ["Instructions", "אופן ההכנה"],      all_headers)
    description_block  = extract_block(text, ["Description",  "תיאור"],           all_headers)

    return (
        title,
        parse_list(ingredients_block),
        parse_steps(instructions_block),
        description_block.strip(),
    )


# ---------- Shared CSS helpers ------------------------------

def _css_side(is_he: bool, side: str) -> str:
    """Return 'right' or 'left' depending on language and requested logical side."""
    if side == "start":
        return "right" if is_he else "left"
    return "left" if is_he else "right"


def _shared_list_css(is_he: bool) -> str:
    s = _css_side(is_he, "start")
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
) -> str:
    is_he     = lang == "he"
    direction = "rtl" if is_he else "ltr"
    font      = "Alef, system-ui, sans-serif" if is_he else \
                "system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif"

    L = {
        "tag":         "מתכון"       if is_he else "RECIPE",
        "time":        "זמן"         if is_he else "Time",
        "servings":    "מנות"        if is_he else "Servings",
        "level":       "רמת קושי"    if is_he else "Level",
        "ingredients": "מצרכים"      if is_he else "Ingredients",
        "instructions":"הוראות הכנה" if is_he else "Instructions",
        "subtitle":    "מנה קלאסית שקל להכין בבית." if is_he else
                       "A classic dish you can easily make at home.",
        "print":       "הדפסה"       if is_he else "Print",
        "switch_link": '<img src="flag_gb.png" alt="English"> English' if is_he else
                       '<img src="flag_il.png" alt="עברית"> עברית',
    }

    hero_tag = f'<img class="hero" src="{hero_image}" alt="{title}">' if hero_image else ""
    list_css = _shared_list_css(is_he)

    return f"""<!DOCTYPE html>
<html lang="{lang}" dir="{direction}">
<head>
<meta charset="UTF-8">
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
    padding: 40px;
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
.lang-switch {{
    position: absolute;
    top: 16px;
    right: 16px;
    font-size: 14px;
    z-index: 15;
    display: flex;
    align-items: center;
    gap: 4px;
    text-decoration: none;
    color: inherit;
}}
.lang-switch img {{ width: 20px; height: 14px; }}
.print-button {{
    position: absolute;
    top: 16px;
    left: 16px;
    padding: 4px 10px;
    font-size: 13px;
    border: none;
    border-radius: 5px;
    background: var(--orange);
    color: white;
    cursor: pointer;
    z-index: 20;
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
h1 {{
    margin: 6px 0;
    font-size: 32px;
    color: var(--orange);
}}
.subtitle  {{ font-size: 15px; color: #666; margin-bottom: 6px; }}
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
h2 {{
    font-size: 20px;
    margin-bottom: 10px;
    color: var(--orange);
}}
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

  <button class="print-button" onclick="window.print()">🖨️ {L['print']}</button>
  <a class="lang-switch" href="{file_other}">{L['switch_link']}</a>

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
:root {{
    --orange: #d35400;
    --section-bg: #fffaf0;
    --border: #f7d8c5;
}}
body {{
    font-family: Georgia, serif;
    padding: 40px;
    max-width: 800px;
    margin: auto;
    line-height: 1.5;
    background: #fff;
}}
h1  {{ font-size: 32px; margin-bottom: 10px; color: var(--orange); }}
h2  {{ margin-top: 28px; border-bottom: 2px solid var(--orange);
       padding-bottom: 4px; color: var(--orange); }}
.section-box {{
    background: var(--section-bg);
    border: 1px solid var(--border);
    border-radius: 10px;
    padding: 16px;
    margin-bottom: 16px;
}}
.divider {{
    border-top: 1px dashed var(--orange);
    margin: 20px 0;
}}
.print-button {{
    display: inline-block;
    margin-bottom: 20px;
    padding: 8px 12px;
    font-size: 14px;
    border: none;
    border-radius: 6px;
    background: var(--orange);
    color: white;
    cursor: pointer;
}}
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
    name = RECIPE_NAME

    # חיפוש תמונה אוטומטי
    image_file = None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        p = Path(f"{name}{ext}")
        if p.exists():
            image_file = str(p)
            break
    if not image_file:
        print(f"⚠️  לא נמצאה תמונה עבור '{name}' — המתכון ייווצר בלי תמונה.")

    file_en = f"{name}_en.html"
    file_he = f"{name}_he.html"

    # English
    try:
        t, ing, inst, desc = parse_recipe_file(f"{name}_en.txt")
    except FileNotFoundError:
        print(f"❌  הקובץ {name}_en.txt לא נמצא. מוודא שהוא קיים ומנסה שוב.")
        return

    Path(file_en).write_text(
        build_html(t, ing, inst, desc,
                   lang="en", time_text=TIME_EN, level_text=LEVEL_EN,
                   servings=SERVINGS, hero_image=image_file, file_other=file_he),
        encoding="utf-8",
    )
    Path(f"{name}_en_print.html").write_text(
        build_print(t, ing, inst, desc, lang="en"),
        encoding="utf-8",
    )

    # Hebrew
    try:
        t, ing, inst, desc = parse_recipe_file(f"{name}_he.txt")
    except FileNotFoundError:
        print(f"❌  הקובץ {name}_he.txt לא נמצא. מוודא שהוא קיים ומנסה שוב.")
        return

    Path(file_he).write_text(
        build_html(t, ing, inst, desc,
                   lang="he", time_text=TIME_HE, level_text=LEVEL_HE,
                   servings=SERVINGS, hero_image=image_file, file_other=file_en),
        encoding="utf-8",
    )
    Path(f"{name}_he_print.html").write_text(
        build_print(t, ing, inst, desc, lang="he"),
        encoding="utf-8",
    )

    print(f"✅  נוצרו 4 קבצים: {file_en}, {file_he}, {name}_en_print.html, {name}_he_print.html")


if __name__ == "__main__":
    main()
