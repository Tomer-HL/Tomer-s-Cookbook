"""
app.py — Flask UI for "Tomer's Israeli Cookbook" with edit support
            + automatic git push to GitHub after each save.
            + password-protected login for remote hosting.
"""
from __future__ import annotations

import functools
import json
import os
import re
import shutil
import subprocess
import sys
import threading
import webbrowser
from datetime import datetime
from pathlib import Path

from flask import (Flask, abort, redirect, render_template, request,
                   send_from_directory, session, url_for)

PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

import generate_recipe   # noqa: E402
import generate_index    # noqa: E402

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

# ============================================================
#  Password protection
# ============================================================
EDIT_PASSWORD = os.environ.get("EDIT_PASSWORD", "")


def login_required(f):
    @functools.wraps(f)
    def decorated(*args, **kwargs):
        if EDIT_PASSWORD and not session.get("logged_in"):
            return redirect(url_for("login_view", next=request.path))
        return f(*args, **kwargs)
    return decorated


@app.route("/login", methods=["GET", "POST"])
def login_view():
    error = None
    if request.method == "POST":
        if request.form.get("password") == EDIT_PASSWORD:
            session["logged_in"] = True
            return redirect(request.args.get("next") or url_for("form_view"))
        error = "Wrong password."
    return render_template("login.html", error=error)


@app.route("/logout")
def logout_view():
    session.clear()
    return redirect(url_for("login_view"))

COOKBOOK_DIR  = PROJECT_ROOT / "cookbook"
META_FILENAME = "_meta.json"

LEVELS_EN = ["Easy", "Medium", "Hard"]
LEVELS_HE = ["קל", "בינוני", "מאתגר"]
CATEGORY_LABELS = {
    "entrees":  "Entrees / עיקריות",
    "sides":    "Sides / תוספות",
    "bread":    "Bread & Pastry / לחמים ומאפים",
    "desserts": "Desserts / קינוחים",
}
POSITION_PRESETS = [
    "center center", "top center", "bottom center",
    "left center", "right center", "top left",
    "top right", "bottom left", "bottom right",
]
ALLOWED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
LANG_MODES = {"both", "en", "he"}

_LANG_SWITCH_RE = re.compile(
    r'<a class="lang-switch"[^>]*>.*?</a>', re.IGNORECASE | re.DOTALL,
)


def _sanitize_recipe_name(name: str) -> str:
    name = re.sub(r"\s+", "_", name.strip())
    return re.sub(r"[^A-Za-z0-9_\-]", "", name)


def _build_txt(*, title, description, ingredients, instructions,
               img_position, img_zoom, lang):
    is_he = lang == "he"
    L = {"desc": "תיאור" if is_he else "Description",
         "ing":  "מצרכים" if is_he else "Ingredients",
         "inst": "אופן ההכנה" if is_he else "Instructions"}
    return (f"{title.strip()}\n\n"
            f"Position: {img_position}\nZoom: {img_zoom}\n\n"
            f"{L['desc']}\n{description.strip()}\n\n"
            f"{L['ing']}\n{ingredients.strip()}\n\n"
            f"{L['inst']}\n{instructions.strip()}\n")


def _save_uploaded_image(file_storage, recipe_name):
    if not file_storage or not file_storage.filename:
        return None
    ext = Path(file_storage.filename).suffix.lower()
    if ext not in ALLOWED_IMAGE_EXTS:
        return None
    target = PROJECT_ROOT / f"{recipe_name}{ext}"
    file_storage.save(str(target))
    return target


def _save_meta(out_dir, *, lang_mode, category, servings,
               time_en, time_he, level_en, level_he,
               img_position, img_zoom):
    meta = {"lang_mode": lang_mode, "category": category, "servings": servings,
            "time_en": time_en, "time_he": time_he,
            "level_en": level_en, "level_he": level_he,
            "img_position": img_position, "img_zoom": img_zoom}
    (out_dir / META_FILENAME).write_text(
        json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def _parse_txt_for_edit(txt_path, lang):
    is_he = lang == "he"
    label_desc = "תיאור" if is_he else "Description"
    label_ing  = "מצרכים" if is_he else "Ingredients"
    label_inst = "אופן ההכנה" if is_he else "Instructions"
    labels = {label_desc, label_ing, label_inst}

    lines = txt_path.read_text(encoding="utf-8").split("\n")
    i = 0
    while i < len(lines) and not lines[i].strip():
        i += 1
    title = lines[i].strip() if i < len(lines) else ""
    i += 1
    while i < len(lines) and not lines[i].strip():
        i += 1

    pos, zoom = "center center", "100%"
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith("Position:"):
            pos = s.split(":", 1)[1].strip(); i += 1
        elif s.startswith("Zoom:"):
            zoom = s.split(":", 1)[1].strip(); i += 1
        elif not s:
            i += 1; break
        else:
            break

    sections = {label_desc: [], label_ing: [], label_inst: []}
    current = None
    while i < len(lines):
        line = lines[i]; s = line.strip()
        if s in labels:
            current = s
        elif current is not None:
            sections[current].append(line)
        i += 1

    def _join(ls):
        return "\n".join(ls).strip("\n").rstrip()

    return {"title": title,
            "description":  _join(sections[label_desc]),
            "ingredients":  _join(sections[label_ing]),
            "instructions": _join(sections[label_inst]),
            "img_position": pos, "img_zoom": zoom}


def _generate_single_language(*, lang, recipe_name, category,
                              title, description, ingredients, instructions,
                              time_text, level_text, servings,
                              img_position, img_zoom, image_storage):
    out_dir = COOKBOOK_DIR / category / recipe_name
    out_dir.mkdir(parents=True, exist_ok=True)

    txt_content = _build_txt(title=title, description=description,
                             ingredients=ingredients, instructions=instructions,
                             img_position=img_position, img_zoom=img_zoom, lang=lang)
    txt_path = out_dir / f"{recipe_name}_{lang}.txt"
    txt_path.write_text(txt_content, encoding="utf-8")

    title_p, ingredients_p, instructions_p, description_p, pos, zoom = (
        generate_recipe.parse_recipe_file(str(txt_path)))

    image_filename = None
    src_img = _save_uploaded_image(image_storage, recipe_name)
    if src_img:
        dst_img = out_dir / src_img.name
        generate_recipe.process_hero_image(src_img, dst_img, position=pos)
        image_filename = src_img.name
        if src_img.exists() and src_img.resolve() != dst_img.resolve():
            src_img.unlink()
    else:
        for ext in ALLOWED_IMAGE_EXTS:
            candidate = out_dir / f"{recipe_name}{ext}"
            if candidate.exists():
                image_filename = candidate.name; break

    html = generate_recipe.build_html(
        title_p, ingredients_p, instructions_p, description_p,
        lang=lang, time_text=time_text, level_text=level_text,
        servings=servings, hero_image=image_filename,
        img_position=pos, img_zoom=zoom, file_other="#")
    html = _LANG_SWITCH_RE.sub("", html)
    (out_dir / f"{recipe_name}_{lang}.html").write_text(html, encoding="utf-8")

    print_html = generate_recipe.build_print(
        title_p, ingredients_p, instructions_p, description_p, lang=lang)
    (out_dir / f"{recipe_name}_{lang}_print.html").write_text(print_html, encoding="utf-8")


def _existing_recipes():
    items = []
    if not COOKBOOK_DIR.exists():
        return items
    for cat in generate_index.CATEGORIES_ORDER:
        cat_dir = COOKBOOK_DIR / cat
        if not cat_dir.exists(): continue
        for recipe_dir in sorted(cat_dir.iterdir()):
            if not recipe_dir.is_dir(): continue
            html_en = recipe_dir / f"{recipe_dir.name}_en.html"
            html_he = recipe_dir / f"{recipe_dir.name}_he.html"
            if html_en.exists() or html_he.exists():
                items.append({
                    "name": recipe_dir.name, "category": cat,
                    "url_en": (f"/cookbook/{cat}/{recipe_dir.name}/{recipe_dir.name}_en.html"
                               if html_en.exists() else None),
                    "url_he": (f"/cookbook/{cat}/{recipe_dir.name}/{recipe_dir.name}_he.html"
                               if html_he.exists() else None),
                    "edit_url": f"/edit/{cat}/{recipe_dir.name}",
                })
    return items


# ============================================================
#  Auto-push to GitHub after every save
# ============================================================
def _git(*args, timeout=60):
    """Run a git command in the project directory. Returns CompletedProcess."""
    return subprocess.run(
        ["git", *args],
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _push_to_github(recipe_name: str) -> None:
    """Stage, commit, and push changes to GitHub. Logs to stdout.

    Designed to be safe to call from a background thread - never raises.
    Failures are printed to the terminal but don't block the user.
    """
    try:
        # Stage all changes (cookbook/, *.txt, *.png, etc.)
        add = _git("add", ".")
        if add.returncode != 0:
            print(f"[GIT] add failed: {add.stderr.strip()}")
            return

        # Anything to commit?
        diff = _git("diff", "--cached", "--quiet")
        if diff.returncode == 0:
            print("[GIT] No changes to commit.")
            return

        # Commit
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
        msg = f"Update recipe: {recipe_name} - {timestamp}"
        commit = _git("commit", "-m", msg)
        if commit.returncode != 0:
            print(f"[GIT] commit failed: {commit.stderr.strip()}")
            return
        print(f"[GIT] Committed: {msg}")

        # Push
        push = _git("push", "origin", "main", timeout=120)
        if push.returncode != 0:
            print(f"[GIT] push failed: {push.stderr.strip()}")
            return
        print("[GIT] Pushed to GitHub successfully. "
              "Site will refresh on GitHub Pages within ~30s.")

    except subprocess.TimeoutExpired:
        print("[GIT] Operation timed out.")
    except Exception as exc:
        print(f"[GIT] Unexpected error: {exc}")


def _push_to_github_async(recipe_name: str) -> None:
    """Run _push_to_github in a background thread so the user doesn't wait."""
    threading.Thread(
        target=_push_to_github, args=(recipe_name,), daemon=True
    ).start()


@app.route("/")
def index_view():
    """Public cookbook index — serves the generated Hebrew index page."""
    idx = COOKBOOK_DIR / "index_he.html"
    if not idx.exists():
        generate_index.main()
    return send_from_directory(str(COOKBOOK_DIR), "index_he.html")


@app.route("/admin")
@login_required
def form_view():
    return render_template("form.html",
        categories=CATEGORY_LABELS, levels_en=LEVELS_EN, levels_he=LEVELS_HE,
        position_presets=POSITION_PRESETS, existing=_existing_recipes(),
        prefill=None, is_edit=False, existing_image=None)


@app.route("/edit/<category>/<recipe>")
@login_required
def edit_view(category, recipe):
    out_dir = COOKBOOK_DIR / category / recipe
    if not out_dir.exists():
        abort(404, description=f"Recipe not found: {category}/{recipe}")

    meta_path = out_dir / META_FILENAME
    if meta_path.exists():
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
    else:
        has_en = (out_dir / f"{recipe}_en.txt").exists()
        has_he = (out_dir / f"{recipe}_he.txt").exists()
        if has_en and has_he: lm = "both"
        elif has_en: lm = "en"
        elif has_he: lm = "he"
        else: abort(404, description="No saved TXT files for this recipe.")
        meta = {"lang_mode": lm, "category": category, "servings": 4,
                "time_en": "30 minutes", "time_he": "30 דקות",
                "level_en": "Easy", "level_he": "קל",
                "img_position": "center center", "img_zoom": "100%"}

    prefill = {
        "lang_mode": meta.get("lang_mode", "both"),
        "recipe_name": recipe,
        "category": meta.get("category", category),
        "servings": meta.get("servings", 4),
        "time_en": meta.get("time_en", "30 minutes"),
        "time_he": meta.get("time_he", "30 דקות"),
        "level_en": meta.get("level_en", "Easy"),
        "level_he": meta.get("level_he", "קל"),
        "img_position": meta.get("img_position", "center center"),
        "img_zoom": meta.get("img_zoom", "100%"),
        "title_en": "", "title_he": "",
        "description_en": "", "description_he": "",
        "ingredients_en": "", "ingredients_he": "",
        "instructions_en": "", "instructions_he": "",
    }

    en_txt = out_dir / f"{recipe}_en.txt"
    if en_txt.exists():
        d = _parse_txt_for_edit(en_txt, "en")
        prefill["title_en"] = d["title"]
        prefill["description_en"] = d["description"]
        prefill["ingredients_en"] = d["ingredients"]
        prefill["instructions_en"] = d["instructions"]
        prefill["img_position"] = d["img_position"]
        prefill["img_zoom"] = d["img_zoom"]

    he_txt = out_dir / f"{recipe}_he.txt"
    if he_txt.exists():
        d = _parse_txt_for_edit(he_txt, "he")
        prefill["title_he"] = d["title"]
        prefill["description_he"] = d["description"]
        prefill["ingredients_he"] = d["ingredients"]
        prefill["instructions_he"] = d["instructions"]

    existing_image = None
    for ext in ALLOWED_IMAGE_EXTS:
        if (out_dir / f"{recipe}{ext}").exists():
            existing_image = f"/cookbook/{category}/{recipe}/{recipe}{ext}"
            break

    return render_template("form.html",
        categories=CATEGORY_LABELS, levels_en=LEVELS_EN, levels_he=LEVELS_HE,
        position_presets=POSITION_PRESETS, existing=_existing_recipes(),
        prefill=prefill, is_edit=True, existing_image=existing_image)


@app.route("/create", methods=["POST"])
@login_required
def create_view():
    f = request.form
    lang_mode = f.get("lang_mode", "both")
    if lang_mode not in LANG_MODES:
        abort(400, description=f"Invalid language mode: {lang_mode}")

    recipe_name = _sanitize_recipe_name(f.get("recipe_name", ""))
    if not recipe_name:
        abort(400, description="Recipe name is required.")

    category = f.get("category", "")
    if category not in generate_recipe.VALID_CATEGORIES:
        abort(400, description=f"Invalid category: {category}")

    try: servings = int(f.get("servings", "4"))
    except ValueError: servings = 4
    servings = max(1, min(99, servings))

    img_position = (f.get("img_position", "") or "center center").strip() or "center center"
    img_zoom_raw = (f.get("img_zoom", "") or "100").strip() or "100"
    if not img_zoom_raw.endswith("%"):
        img_zoom_raw = f"{img_zoom_raw}%"
    img_zoom = img_zoom_raw

    title_en = f.get("title_en", "").strip()
    title_he = f.get("title_he", "").strip()
    if lang_mode in ("both", "en") and not title_en:
        abort(400, description="English title is required.")
    if lang_mode in ("both", "he") and not title_he:
        abort(400, description="Hebrew title is required.")

    time_en  = (f.get("time_en", "")  or "").strip() or "30 minutes"
    time_he  = (f.get("time_he", "")  or "").strip() or "30 דקות"
    level_en = (f.get("level_en", "") or "Easy").strip()
    level_he = (f.get("level_he", "") or "קל").strip()

    desc_en = f.get("description_en", "")
    desc_he = f.get("description_he", "")
    ing_en  = f.get("ingredients_en", "")
    ing_he  = f.get("ingredients_he", "")
    inst_en = f.get("instructions_en", "")
    inst_he = f.get("instructions_he", "")

    image_storage = request.files.get("image")
    os.chdir(PROJECT_ROOT)

    out_dir = COOKBOOK_DIR / category / recipe_name

    try:
        if lang_mode == "both":
            (PROJECT_ROOT / f"{recipe_name}_en.txt").write_text(
                _build_txt(title=title_en, description=desc_en, ingredients=ing_en,
                           instructions=inst_en, img_position=img_position,
                           img_zoom=img_zoom, lang="en"), encoding="utf-8")
            (PROJECT_ROOT / f"{recipe_name}_he.txt").write_text(
                _build_txt(title=title_he, description=desc_he, ingredients=ing_he,
                           instructions=inst_he, img_position=img_position,
                           img_zoom=img_zoom, lang="he"), encoding="utf-8")

            new_img = _save_uploaded_image(image_storage, recipe_name)
            if not new_img:
                # Reuse existing image from recipe folder if no new upload
                for ext in ALLOWED_IMAGE_EXTS:
                    existing = out_dir / f"{recipe_name}{ext}"
                    if existing.exists():
                        shutil.copy2(existing, PROJECT_ROOT / f"{recipe_name}{ext}")
                        break

            generate_recipe.RECIPE_NAME = recipe_name
            generate_recipe.CATEGORY    = category
            generate_recipe.TIME_EN     = time_en
            generate_recipe.TIME_HE     = time_he
            generate_recipe.LEVEL_EN    = level_en
            generate_recipe.LEVEL_HE    = level_he
            generate_recipe.SERVINGS    = servings
            generate_recipe.main()

        elif lang_mode == "en":
            _generate_single_language(
                lang="en", recipe_name=recipe_name, category=category,
                title=title_en, description=desc_en,
                ingredients=ing_en, instructions=inst_en,
                time_text=time_en, level_text=level_en, servings=servings,
                img_position=img_position, img_zoom=img_zoom,
                image_storage=image_storage)
            # Cleanup HE files if reducing scope from bilingual
            for fname in (f"{recipe_name}_he.html", f"{recipe_name}_he_print.html",
                          f"{recipe_name}_he.txt"):
                fp = out_dir / fname
                if fp.exists(): fp.unlink()
        else:
            _generate_single_language(
                lang="he", recipe_name=recipe_name, category=category,
                title=title_he, description=desc_he,
                ingredients=ing_he, instructions=inst_he,
                time_text=time_he, level_text=level_he, servings=servings,
                img_position=img_position, img_zoom=img_zoom,
                image_storage=image_storage)
            for fname in (f"{recipe_name}_en.html", f"{recipe_name}_en_print.html",
                          f"{recipe_name}_en.txt"):
                fp = out_dir / fname
                if fp.exists(): fp.unlink()

        out_dir.mkdir(parents=True, exist_ok=True)
        _save_meta(out_dir, lang_mode=lang_mode, category=category, servings=servings,
                   time_en=time_en, time_he=time_he,
                   level_en=level_en, level_he=level_he,
                   img_position=img_position, img_zoom=img_zoom)

        generate_index.main()

    except Exception as exc:
        return render_template("error.html", message=str(exc)), 500

    # Push to GitHub in the background so the user gets a fast redirect.
    # Errors are logged to the terminal but never block the save.
    _push_to_github_async(recipe_name)

    return redirect(url_for("success_view",
        category=category, recipe=recipe_name, lang_mode=lang_mode))


@app.route("/success/<category>/<recipe>")
@login_required
def success_view(category, recipe):
    lang_mode = request.args.get("lang_mode", "both")
    if lang_mode not in LANG_MODES: lang_mode = "both"
    return render_template("success.html",
        category=category, recipe=recipe, lang_mode=lang_mode)


@app.route("/cookbook/")
def cookbook_index():
    return send_from_directory(str(COOKBOOK_DIR), "index_en.html")


@app.route("/cookbook/<path:subpath>")
def cookbook_files(subpath):
    full = COOKBOOK_DIR / subpath
    if full.is_dir():
        return send_from_directory(str(full), "index_en.html")
    return send_from_directory(str(COOKBOOK_DIR), subpath)


@app.route("/<path:subpath>")
def root_cookbook_files(subpath):
    """Serve cookbook assets at root-relative paths.

    index_he.html is sent from COOKBOOK_DIR at URL /, so its relative
    hrefs (entrees/…, flag_gb.png, …) resolve to /<subpath>.  This route
    forwards those requests to the same directory so images and recipe
    pages work correctly.
    """
    full = COOKBOOK_DIR / subpath
    if full.is_dir():
        return send_from_directory(str(full), "index_en.html")
    return send_from_directory(str(COOKBOOK_DIR), subpath)


def _configure_git_credentials() -> None:
    """Set the git remote URL to include the GitHub token for HTTPS pushes.
    Reads GITHUB_TOKEN and GITHUB_REPO from environment variables.
    GITHUB_REPO format: owner/repo  (e.g. tomer-hl/Tomer-s-Cookbook)
    """
    token = os.environ.get("GITHUB_TOKEN", "")
    repo  = os.environ.get("GITHUB_REPO", "")
    if not token or not repo:
        return
    remote_url = f"https://{token}@github.com/{repo}.git"
    # set-url fails if origin doesn't exist yet — fall back to add
    result = _git("remote", "set-url", "origin", remote_url)
    if result.returncode != 0:
        _git("remote", "add", "origin", remote_url)
    _git("config", "user.email", os.environ.get("GIT_EMAIL", "cookbook@app.local"))
    _git("config", "user.name",  os.environ.get("GIT_NAME",  "Cookbook App"))
    print("[GIT] Credentials configured.")


def _startup_pull() -> None:
    """Pull latest recipes from GitHub so the server has up-to-date content."""
    _configure_git_credentials()
    result = _git("pull", "--rebase", "origin", "main", timeout=60)
    if result.returncode == 0:
        print("[GIT] Pulled latest from GitHub.")
    else:
        print(f"[GIT] Pull failed (non-fatal): {result.stderr.strip()}")


def _open_browser():
    webbrowser.open("http://localhost:5000")


# Run startup sync once (guard against Werkzeug reloader double-import)
if not os.environ.get("WERKZEUG_RUN_MAIN"):
    _startup_pull()

if __name__ == "__main__":
    is_local = not os.environ.get("RENDER") and not os.environ.get("RAILWAY_ENVIRONMENT")
    if is_local and not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Timer(1.2, _open_browser).start()
    host = "0.0.0.0" if (os.environ.get("RENDER") or os.environ.get("RAILWAY_ENVIRONMENT")) else "127.0.0.1"
    port = int(os.environ.get("PORT", 5000))
    app.run(host=host, port=port, debug=False)