import re
from pathlib import Path

# PIL (Pillow) דרוש רק אם רוצים עיבוד אוטומטי של התמונה ליחס 16:9.
# אם לא מותקן — הסקריפט ימשיך לעבוד אבל התמונה תועתק כמות שהיא.
try:
    from PIL import Image
    _HAS_PIL = True
except ImportError:
    _HAS_PIL = False

# ממדי ה-hero.
# HERO_HEIGHT_PX  — גובה הקופסה ב-CSS (שנה כאן אם רוצים hero גבוה/נמוך יותר).
# HERO_RATIO      — יחס רוחב:גובה של התמונה המעובדת. מחושב מרוחב התיבה הפנימי
#                   של העמוד (max-width 900px - padding 32px משני הצדדים ≈ 836px).
HERO_HEIGHT_PX    = 260
HERO_RATIO        = 836 / HERO_HEIGHT_PX     # ≈ 3.215 : 1
HERO_TARGET_WIDTH = 1600                     # שדרוג/הקטנה אחידים לרוחב פיקסלי

# ============================================================
#  ⚙️  הגדרות המתכון — שנה רק כאן
# ============================================================

RECIPE_NAME   = "Matbucha"         # שם קובץ (ללא סיומת)
CATEGORY      = "sides"          # entrees | sides | bread | desserts
TIME_EN       = "1 1/2 hours"
TIME_HE       = "1 1/2 שעות"
LEVEL_EN      = "Medium"             # Easy | Medium | Hard
LEVEL_HE      = "בינוני"               # קל | בינוני | מאתגר
SERVINGS      = 6

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
#  📸  הגדרות תמונה בקובץ ה-TXT של המתכון
#  הוסף את השורות האלה (אופציונלי) לכל קובץ טקסט:
#
#  Position: <ערך>     — מיקום החיתוך בתמונה
#  Zoom:     <ערך>%    — הגדלה/הקטנה של התמונה
#
#  ── Position — ערכים נפוצים ──────────────────────────────
#  center center   אמצע אמצע (ברירת מחדל)
#  top center      חלק עליון, מרכז — טוב למנות עם גובה
#  bottom center   חלק תחתון, מרכז — טוב לצלחות מלאות
#  left center     שמאל, מרכז
#  right center    ימין, מרכז
#  top left        פינה שמאל עליונה
#  top right       פינה ימין עליונה
#  20% 35%         מדויק: 20% מהשמאל, 35% מלמעלה
#                  (כל ערך 0%–100% תקין)
#
#  ── Zoom — ערכים ──────────────────────────────────────────
#  100%   ללא שינוי (ברירת מחדל)
#  110%   זום קל פנימה
#  125%   זום בינוני — מגדיל ומסיר שוליים
#  150%   זום חזק — מתמקד בחלק קטן של התמונה
#  80%    זום החוצה — מראה יותר מהתמונה (עם שוליים)
#
#  ── דוגמאות ───────────────────────────────────────────────
#  Position: top center        # עוגה שהגבהה חשובה
#  Position: 50% 30%           # קצת מעל האמצע
#  Zoom: 130%                  # זום אין לפרטים
# ============================================================

# ============================================================
#  סוף הגדרות — אל תשנה מתחת לכאן
# ============================================================

VALID_CATEGORIES = {
    "entrees":  {"en": "Entrees",         "he": "עיקריות"},
    "sides":    {"en": "Sides",           "he": "תוספות"},
    "bread":    {"en": "Bread & Pastry",  "he": "לחמים ומאפים"},
    "desserts": {"en": "Desserts",        "he": "קינוחים"},
}


# ---------- Image processing --------------------------------

def _parse_position_anchors(position: str) -> tuple[float, float]:
    """מחזיר (h_anchor, v_anchor) בטווח 0.0-1.0 לפי מחרוזת Position.
    0.0 = שמאל/למעלה, 0.5 = אמצע, 1.0 = ימין/למטה."""
    pos = position.lower().strip()

    # תמיכה בפורמט מפורש עם אחוזים: "20% 35%"
    pct = re.findall(r"(\d+(?:\.\d+)?)\s*%", pos)
    if len(pct) >= 2:
        return float(pct[0]) / 100, float(pct[1]) / 100

    # פורמט מילולי: "top center", "bottom left", וכו'
    h = 0.0 if "left"  in pos else 1.0 if "right"  in pos else 0.5
    v = 0.0 if "top"   in pos else 1.0 if "bottom" in pos else 0.5
    return h, v


def process_hero_image(src: Path, dst: Path, position: str = "center center",
                        target_ratio: float = HERO_RATIO) -> bool:
    """חותך את התמונה ליחס היעד (ברירת מחדל 16:9) לפי ה-Position שנבחר.
    מחזיר True אם התמונה עובדה בהצלחה, False אם Pillow לא מותקן (אז העתקה ישירה)."""
    if not _HAS_PIL:
        if src.resolve() != dst.resolve():
            dst.write_bytes(src.read_bytes())
        return False

    img = Image.open(src)
    # שמירת EXIF orientation (תמונות מהטלפון לעיתים מסובבות)
    try:
        from PIL import ImageOps
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass

    w, h = img.size
    current_ratio = w / h
    h_anchor, v_anchor = _parse_position_anchors(position)

    # חיתוך ליחס היעד
    if abs(current_ratio - target_ratio) < 0.005:
        cropped = img                                    # כבר ביחס הנכון
    elif current_ratio > target_ratio:
        # תמונה רחבה מדי — חיתוך משמאל/ימין
        new_w = int(round(h * target_ratio))
        left  = int(round((w - new_w) * h_anchor))
        cropped = img.crop((left, 0, left + new_w, h))
    else:
        # תמונה גבוהה מדי — חיתוך מלמעלה/מלמטה
        new_h = int(round(w / target_ratio))
        top   = int(round((h - new_h) * v_anchor))
        cropped = img.crop((0, top, w, top + new_h))

    # הקטנה אם התמונה גדולה מהרוחב היעד (חוסך משקל בדפדפן)
    if cropped.size[0] > HERO_TARGET_WIDTH:
        new_h = int(round(HERO_TARGET_WIDTH / target_ratio))
        cropped = cropped.resize((HERO_TARGET_WIDTH, new_h), Image.LANCZOS)

    # שמירה בפורמט המקורי
    ext = dst.suffix.lower()
    if ext in (".jpg", ".jpeg"):
        if cropped.mode != "RGB":
            cropped = cropped.convert("RGB")
        cropped.save(dst, quality=88, optimize=True)
    elif ext == ".webp":
        cropped.save(dst, quality=88, method=6)
    else:  # .png או אחר
        cropped.save(dst, optimize=True)
    return True


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


def parse_recipe_file(path: str) -> tuple[str, list[str], list[str], str, str, str]:
    text  = Path(path).read_text(encoding="utf-8")
    title = text.splitlines()[0].strip()
    all_h = ["Ingredients", "Instructions", "Description",
             "מצרכים", "אופן ההכנה", "תיאור"]

    # חילוץ Position: ו-Zoom: (אופציונלי — ברירת מחדל: center center / 100%)
    position = "center center"
    zoom     = "100%"
    for line in text.splitlines():
        m = re.match(r"^\s*Position\s*:\s*(.+)", line, re.IGNORECASE)
        if m:
            position = m.group(1).strip()
        m = re.match(r"^\s*Zoom\s*:\s*(.+)", line, re.IGNORECASE)
        if m:
            zoom = m.group(1).strip()

    return (
        title,
        parse_list(extract_block(text, ["Ingredients", "מצרכים"], all_h)),
        parse_steps(extract_block(text, ["Instructions", "אופן ההכנה"], all_h)),
        extract_block(text, ["Description", "תיאור"], all_h).strip(),
        position,
        zoom,
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
}}
/* כותרת משנה בתוך פריט רשימת מצרכים — נראית כמו סעיף, לא כמו פריט */
ul li.ing-heading {{
    list-style: none;
    padding-{s}: 0;
    margin-top: 14px;
    margin-bottom: 6px;
    font-weight: 700;
    color: var(--orange);
    font-size: 16px;
}}
ul li.ing-heading:first-child {{ margin-top: 0; }}
ul li.ing-heading::before {{ content: none; }}
/* כותרת משנה בתחילת צעד (ב-ol) */
ol li .step-heading {{
    display: inline-block;
    color: var(--orange);
    font-weight: 700;
    margin-bottom: 4px;
}}"""


# ---------- Inline text formatter ---------------------------

# ** ** מסביב לטקסט → <strong>...</strong> (בסגנון Markdown).
#    דוגמה ב-TXT:  **תחמיץ לבן**, **Prepare the batter:**
_BOLD_RE = re.compile(r"\*\*(.+?)\*\*", re.DOTALL)

def _format_inline(text: str) -> str:
    """מחיל פורמטינג inline על טקסט: **bold** → <strong>bold</strong>."""
    return _BOLD_RE.sub(r"<strong>\1</strong>", text)


def _split_subheading(step: str) -> tuple[str, str]:
    """אם השורה הראשונה של הצעד היא כותרת משנה (נגמרת בנקודותיים ולא
    מכילה טקסט נוסף אחרי), מחזיר (כותרת, שאר הצעד). אחרת מחזיר ("", step)."""
    lines = step.split("\n", 1)
    if len(lines) == 2:
        first, rest = lines[0].strip(), lines[1].strip()
        # כותרת משנה = שורה קצרה יחסית שנגמרת ב-":" ללא טקסט אחר אחרי
        if first.endswith(":") and len(first) <= 80 and "\n" not in first:
            return first, rest
    return "", step


def _render_ingredients(ingredients: list[str]) -> str:
    """שורות שנגמרות בנקודותיים — כותרות משנה (קטגוריות). שאר השורות — פריטי רשימה.
    בנוסף, ** ** מומר ל-<strong>."""
    out: list[str] = []
    for item in ingredients:
        stripped = item.strip()
        is_heading = stripped.endswith(":") and len(stripped) <= 80
        formatted  = _format_inline(stripped.rstrip(":") if is_heading else stripped)
        if is_heading:
            out.append(f'<li class="ing-heading">{formatted}</li>')
        else:
            out.append(f"<li>{formatted}</li>")
    return "".join(out)


def _render_steps(steps: list[str]) -> str:
    """מזהה אוטומטית כותרת משנה (שורה ראשונה שנגמרת בנקודותיים) ומדגיש אותה.
    בנוסף, ** ** מומר ל-<strong> בכל מקום."""
    out: list[str] = []
    for step in steps:
        heading, body = _split_subheading(step)
        body_html = _format_inline(body).replace("\n", "<br>")
        if heading:
            heading_html = _format_inline(heading.rstrip(":"))
            out.append(
                f'<li><strong class="step-heading">{heading_html}</strong>'
                f'<br>{body_html}</li>'
            )
        else:
            out.append(f"<li>{body_html}</li>")
    return "".join(out)


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
    img_position: str = "top center",
    img_zoom: str     = "80%",
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

    # התמונה כבר עברה עיבוד מוקדם בפונקציית process_hero_image —
    # היא נחתכה ליחס 16:9 לפי Position. לכן כאן צריך רק cover פשוט.
    # Zoom נשאר פעיל כ-CSS transform לזום משני (מעל החיתוך).
    zoom_val    = float(img_zoom.rstrip("%"))
    scale_ratio = zoom_val / 100
    hero_tag = (
        f'''<div class="hero-wrapper">'''
        f'''<div class="hero" role="img" aria-label="{title}" '''
        f'''style="background-image: url('{hero_image}'); '''
        f'''background-position: {img_position}; '''
        f'''transform: scale({scale_ratio}); '''
        f'''transform-origin: {img_position};"></div>'''
        f'''</div>'''
    ) if hero_image else ""
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
.hero-wrapper {{
    position: relative;
    width: 100%;
    height: {HERO_HEIGHT_PX}px; /* גובה קבוע (ברירת מחדל 260px) */
    border-radius: 14px;
    margin: 20px 0 24px;
    box-shadow: 0 6px 18px rgba(0,0,0,0.12);
    overflow: hidden;           /* חותך את מה שגולש מה-scale */
    background: #f5eee4;        /* fallback אם התמונה לא נטענה */
}}
.hero {{
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    background-size: cover;     /* מתיישב בדיוק — התמונה עובדה לאותו יחס */
    background-repeat: no-repeat;
    /* background-image, background-position, transform, transform-origin
       מוזרקים inline מתוך Python לפי Position ו-Zoom */
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

    # פירסור של שני ה-TXT קודם — נצטרך את ה-Position לפני עיבוד התמונה
    title_en, ing_en, inst_en, desc_en, pos_en, zoom_en = parse_recipe_file(str(txt_en))
    title_he, ing_he, inst_he, desc_he, pos_he, zoom_he = parse_recipe_file(str(txt_he))

    # חיפוש תמונה במקור (לא בתיקיית היעד — נבנה אותה מחדש בכל ריצה)
    src_image: Path | None = None
    for ext in (".png", ".jpg", ".jpeg", ".webp"):
        for loc in [Path("."), out_dir]:
            p = loc / f"{RECIPE_NAME}{ext}"
            if p.exists():
                src_image = p
                break
        if src_image:
            break

    image_file: str | None = None
    if src_image:
        # שני ה-TXT חולקים אותה תמונה — ניקח את ה-Position מה-en כמקור אמת
        dest_image = out_dir / src_image.name
        processed  = process_hero_image(src_image, dest_image, position=pos_en)
        image_file = src_image.name
        if processed:
            print(f"🖼️   Hero image processed → {HERO_RATIO:.2f}:1 ({pos_en}).")
        elif not _HAS_PIL:
            print("⚠️   Pillow לא מותקן — התמונה הועתקה ללא חיתוך. להתקנה: pip install Pillow")
    else:
        print(f"⚠️  No image found for '{RECIPE_NAME}' — Will be created without an image.")

    file_en = f"{RECIPE_NAME}_en.html"
    file_he = f"{RECIPE_NAME}_he.html"

    # English
    (out_dir / file_en).write_text(
        build_html(title_en, ing_en, inst_en, desc_en,
                   lang="en", time_text=TIME_EN, level_text=LEVEL_EN,
                   servings=SERVINGS, hero_image=image_file,
                   img_position=pos_en, img_zoom=zoom_en,
                   file_other=file_he),
        encoding="utf-8",
    )
    (out_dir / f"{RECIPE_NAME}_en_print.html").write_text(
        build_print(title_en, ing_en, inst_en, desc_en, lang="en"), encoding="utf-8"
    )

    # Hebrew
    (out_dir / file_he).write_text(
        build_html(title_he, ing_he, inst_he, desc_he,
                   lang="he", time_text=TIME_HE, level_text=LEVEL_HE,
                   servings=SERVINGS, hero_image=image_file,
                   img_position=pos_he, img_zoom=zoom_he,
                   file_other=file_en),
        encoding="utf-8",
    )
    (out_dir / f"{RECIPE_NAME}_he_print.html").write_text(
        build_print(title_he, ing_he, inst_he, desc_he, lang="he"), encoding="utf-8"
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