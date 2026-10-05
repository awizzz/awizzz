#!/usr/bin/env python3
import base64
import io
import json
import logging
import os
import urllib.request
from datetime import date, datetime, timedelta, timezone
from html import escape
from math import sqrt
from pathlib import Path

from fontTools import subset
from fontTools.ttLib import TTFont

USER = os.getenv("GITHUB_REPOSITORY_OWNER", "awizzz")
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN", "")
HERE = Path(__file__).resolve().parent
OUT = HERE.parent / "assets"
FONTS = {
    "aw-serif": HERE / "fonts/InstrumentSerif-Regular.ttf",
    "aw-italic": HERE / "fonts/InstrumentSerif-Italic.ttf",
    "aw-mono": HERE / "fonts/IBMPlexMono-Regular.ttf",
    "aw-mono-bold": HERE / "fonts/IBMPlexMono-Medium.ttf",
    "aw-sans": HERE / "fonts/InstrumentSans-Regular.ttf",
}
FALLBACK = {
    "aw-serif": "Georgia,serif", "aw-italic": "Georgia,serif", "aw-sans": "Helvetica,Arial,sans-serif",
    "aw-mono": "ui-monospace,monospace", "aw-mono-bold": "ui-monospace,monospace",
}
logging.getLogger("fontTools").setLevel(logging.ERROR)

THEMES = {
    "light": {
        "bg": "#f6f3ec", "line": "#e3ddd0", "rule": "#d8d3c9",
        "ink": "#1d1c1a", "body": "#57524a", "muted": "#7d776e", "accent": "#df5329",
        "block": "#dcd4c4", "block_alt": "#d3cab8", "stars": None,
    },
    "dark": {
        "bg": "#0f1318", "line": "#232b35", "rule": "#2b323c",
        "ink": "#ece7dc", "body": "#b3b0a8", "muted": "#8a9099", "accent": "#ff7247",
        "block": "#1d242d", "block_alt": "#232b35", "stars": "#ece7dc",
    },
}

# Featured repos. Blurbs live here rather than coming from the GitHub description
# so they read the same way as the rest of the README.
PROJECTS = [
    {"repo": "lobby-selector", "kind": "minecraft plugin",
     "blurb": "A server picker for Spigot and Paper networks. Open the menu, pick where you want to go."},
    {"repo": "SkinManager", "kind": "minecraft plugin",
     "blurb": "Grabs skins from the Mojang API and puts them on players automatically."},
    {"repo": "BedrockTabList", "kind": "minecraft plugin",
     "blurb": "Shows in the tab list who's playing on Bedrock and who's on Java."},
    {"repo": "LiquidGlassCord", "kind": "discord theme",
     "blurb": "A Discord theme that goes for the liquid glass look. Nothing but CSS."},
]



def request_json(url, data=None):
    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "awizzz-profile-generator",
        "X-GitHub-Api-Version": "2022-11-28",
    }
    if TOKEN:
        headers["Authorization"] = f"Bearer {TOKEN}"
    body = None if data is None else json.dumps(data).encode()
    if data is not None:
        headers["Content-Type"] = "application/json"
    req = urllib.request.Request(url, data=body, headers=headers)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def api(path):
    return request_json(f"https://api.github.com{path}")


def graphql(query, variables):
    data = request_json("https://api.github.com/graphql", {"query": query, "variables": variables})
    if data.get("errors"):
        raise RuntimeError(data["errors"])
    return data["data"]


_metrics = {}


def text_width(text, family, size):
    if family not in _metrics:
        font = TTFont(FONTS[family])
        _metrics[family] = (font.getBestCmap(), font["hmtx"], font["head"].unitsPerEm)
    cmap, hmtx, upm = _metrics[family]
    return sum(hmtx[cmap.get(ord(c), ".notdef")][0] for c in text) * size / upm


def font_face(family, text):
    font = TTFont(FONTS[family])
    options = subset.Options()
    options.hinting = False
    options.drop_tables += ["meta", "DSIG"]
    options.name_IDs = [1, 2]
    subsetter = subset.Subsetter(options)
    subsetter.populate(text=text)
    subsetter.subset(font)
    font.flavor = "woff"
    buf = io.BytesIO()
    font.save(buf)
    data = base64.b64encode(buf.getvalue()).decode()
    return f'@font-face{{font-family:"{family}";src:url(data:font/woff;base64,{data}) format("woff")}}'


def wrap(text, family, size, width):
    lines, line = [], ""
    for word in text.split():
        candidate = f"{line} {word}".strip()
        if line and text_width(candidate, family, size) > width:
            lines.append(line)
            line = word
        else:
            line = candidate
    return lines + [line] if line else lines


def ago(iso, now):
    days = (now.date() - date.fromisoformat(iso[:10])).days
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    for limit, step, unit in ((14, 1, "day"), (60, 7, "week"), (365, 30, "month"), (10**6, 365, "year")):
        if days < limit:
            n = days // step
            return f"{n} {unit}{'s' if n > 1 else ''} ago"


class Canvas:
    def __init__(self, w, h, theme):
        self.w, self.h, self.c = w, h, THEMES[theme]
        self.parts, self.glyphs = [], {}

    def add(self, s):
        self.parts.append(s)

    def rect(self, x, y, w, h, fill, rx=0, opacity=1):
        op = f' opacity="{opacity}"' if opacity != 1 else ""
        self.add(f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{rx:g}" fill="{fill}"{op}/>')

    def text(self, x, y, s, family, size, fill, anchor="start", spacing=0, words=0):
        self.glyphs[family] = self.glyphs.get(family, "") + s
        ls = (f' letter-spacing="{spacing:g}"' if spacing else "") + (f' word-spacing="{words:g}"' if words else "")
        self.add(f'<text x="{x:g}" y="{y:g}" font-family="{family},{FALLBACK[family]}" font-size="{size:g}" '
                 f'fill="{fill}" text-anchor="{anchor}"{ls}>{escape(s)}</text>')

    def svg(self, title, framed=True):
        faces = "".join(font_face(f, t) for f, t in self.glyphs.items())
        frame = (f'<rect x="0.5" y="0.5" width="{self.w - 1}" height="{self.h - 1}" rx="16" fill="{self.c["bg"]}" '
                 f'stroke="{self.c["line"]}"/>') if framed else ""
        return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{self.w}" height="{self.h}" viewBox="0 0 {self.w} {self.h}" '
                f'role="img"><title>{escape(title)}</title><style>{faces}</style>{frame}' + "".join(self.parts) + "</svg>")


def weekly(days):
    weeks = {}
    for d in days:
        day = date.fromisoformat(d["date"])
        start = day - timedelta(days=(day.weekday() + 1) % 7)
        weeks[start] = weeks.get(start, 0) + d["count"]
    return [weeks[k] for k in sorted(weeks)][-53:]


def make_banner(data, theme, now):
    cv = Canvas(1200, 440, theme)
    c = cv.c

    if c["stars"]:
        seed = 7
        for _ in range(46):
            seed = (seed * 1103515245 + 12345) % 2**31
            x, y = 40 + seed % 1120, 30 + (seed // 1120) % 190
            size = 2 + (seed >> 9) % 2
            cv.rect(x, y, size, size, c["stars"], opacity=round(0.18 + ((seed >> 4) % 40) / 100, 2))

    cv.text(52, 214, "awizz", "aw-italic", 176, c["ink"], spacing=-2)

    latest = data["latest"]
    right = 1144
    cv.text(right, 74, "last push", "aw-mono", 14, c["muted"], "end")
    cv.text(right, 100, f'{latest["name"]} · {ago(latest["pushed_at"], now)}', "aw-mono-bold", 17, c["ink"], "end")
    cv.text(right, 144, "past twelve months", "aw-mono", 14, c["muted"], "end")
    cv.text(right, 170, f'{data["total"]} contributions', "aw-mono-bold", 17, c["ink"], "end")
    cv.text(right, 196, "one column per week ↓", "aw-mono", 14, c["accent"], "end")

    weeks = weekly(data["days"])
    peak = max(weeks) or 1
    pitch, block = 20, 18
    x0 = (1200 - (len(weeks) * pitch - 2)) / 2
    ground = 440 - 30 - block
    for i, count in enumerate(weeks):
        x = x0 + i * pitch
        cv.rect(x, ground, block, block, c["block_alt"], rx=2)
        height = 0 if count == 0 else 1 + round(7 * sqrt(count / peak))
        for level in range(1, height + 1):
            fill = c["accent"] if level == height else (c["block"] if (i + level) % 2 else c["block_alt"])
            cv.rect(x, ground - level * pitch, block, block, fill, rx=2)

    write(f"banner-{theme}.svg", cv.svg(f'awizz. {data["total"]} contributions over the past year, drawn as one column of blocks per week.'))


def make_row(project, number, repo, theme, now, last):
    # No box and no background: the rows sit straight on the page like a table of contents.
    w, x = 800, 70
    lines = wrap(project["blurb"], "aw-sans", 18, 470)
    h = 92 + 26 * len(lines)
    cv = Canvas(w, h, theme)
    c = cv.c
    cv.rect(0, 0, w, 1, c["rule"])
    if last:
        cv.rect(0, h - 1, w, 1, c["rule"])

    cv.text(0, 64, f"{number:02d}", "aw-italic", 30, c["accent"])
    cv.text(x, 64, project["repo"], "aw-serif", 40, c["ink"], spacing=-0.3)
    for i, line in enumerate(lines):
        cv.text(x, 100 + i * 26, line, "aw-sans", 18, c["body"], words=2.5)

    cv.text(w - 30, 60, project["kind"], "aw-mono", 14, c["muted"], "end")
    cv.text(w, 61, "↗", "aw-mono", 17, c["accent"], "end")
    meta = " · ".join(filter(None, [(repo.get("language") or "").lower(), ago(repo["pushed_at"], now) if repo.get("pushed_at") else ""]))
    cv.text(w - 30, 100, meta, "aw-mono", 14, c["muted"], "end")

    write(f'project-{project["repo"]}-{theme}.svg', cv.svg(f'{project["repo"]}: {project["blurb"]}', framed=False))


def write(name, content):
    OUT.mkdir(exist_ok=True)
    (OUT / name).write_text(content, encoding="utf-8")


def fetch():
    repos = api(f"/users/{USER}/repos?per_page=100&type=owner&sort=pushed")
    own = [r for r in repos if not r.get("fork") and r["name"].lower() != USER.lower()]
    now = datetime.now(timezone.utc)
    query = '''query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions weeks{contributionDays{date contributionCount}}}}}}'''
    cal = graphql(query, {"login": USER, "from": (now - timedelta(days=365)).isoformat(), "to": now.isoformat()})
    cal = cal["user"]["contributionsCollection"]["contributionCalendar"]
    by_name = {r["name"]: r for r in repos}
    for p in PROJECTS:
        if p["repo"] not in by_name:
            by_name[p["repo"]] = api(f'/repos/{USER}/{p["repo"]}')
    latest = max(own, key=lambda r: r.get("pushed_at") or "", default={"name": "something new", "pushed_at": now.isoformat()})
    return {
        "days": [{"date": d["date"], "count": d["contributionCount"]} for w in cal["weeks"] for d in w["contributionDays"]],
        "total": cal["totalContributions"],
        "latest": {"name": latest["name"], "pushed_at": latest["pushed_at"]},
        "repos": {name: {"language": r.get("language"), "pushed_at": r.get("pushed_at")} for name, r in by_name.items()},
    }


def render(data, now=None):
    now = now or datetime.now(timezone.utc)
    for theme in THEMES:
        make_banner(data, theme, now)
        for i, project in enumerate(PROJECTS, 1):
            make_row(project, i, data["repos"].get(project["repo"], {}), theme, now, last=i == len(PROJECTS))


def main():
    render(fetch())
    print("profile assets generated")


if __name__ == "__main__":
    main()
