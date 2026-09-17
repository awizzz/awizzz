#!/usr/bin/env python3
import json
import os
import textwrap
import urllib.request
from collections import Counter
from datetime import datetime, timedelta, timezone
from html import escape
from pathlib import Path

USER = os.getenv("GITHUB_REPOSITORY_OWNER", "awizzz")
TOKEN = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN", "")
OUT = Path("assets")
OUT.mkdir(exist_ok=True)
FEATURED = ["LiquidGlassCord", "BedrockTabList", "SkinManager", "lobby-selector"]
STACK = ["Rust", "TypeScript", "JavaScript", "Python", "Java", "Node.js", "React", "Docker", "Linux", "Bash", "PowerShell", "Git", "PostgreSQL", "MySQL", "MongoDB", "Arduino"]

BG = "#0d1117"
CARD = "#111821"
BORDER = "#30363d"
TEXT = "#f0f6fc"
MUTED = "#8b949e"
BLUE = "#58a6ff"
GREEN = "#3fb950"
FONT = "ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,Liberation Mono,monospace"


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


def svg_start(w, h):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}">
<rect width="100%" height="100%" rx="18" fill="{BG}"/>
<style>text{{font-family:{FONT}}}.title{{fill:{TEXT};font-weight:700}}.muted{{fill:{MUTED}}}.blue{{fill:{BLUE}}}</style>'''


def write(name, content):
    (OUT / name).write_text(content, encoding="utf-8")


def clamp(s, n):
    s = (s or "No description yet.").replace("&", "and")
    return s if len(s) <= n else s[: n - 1].rstrip() + "…"


def streaks(days):
    ordered = sorted(days, key=lambda x: x["date"])
    longest = current = run = 0
    today = datetime.now(timezone.utc).date().isoformat()
    for d in ordered:
        if d["contributionCount"] > 0:
            run += 1
            longest = max(longest, run)
        else:
            run = 0
    by_date = {d["date"]: d["contributionCount"] for d in ordered}
    d = datetime.now(timezone.utc).date()
    if by_date.get(d.isoformat(), 0) == 0:
        d -= timedelta(days=1)
    while by_date.get(d.isoformat(), 0) > 0:
        current += 1
        d -= timedelta(days=1)
    return current, longest


def make_header(user, repos, contribution_total):
    latest = next((r for r in sorted(repos, key=lambda r: r.get("pushed_at") or "", reverse=True)
                   if not r.get("fork") and r["name"].lower() != USER.lower()), None)
    latest_name = latest["name"] if latest else "building something new"
    svg = svg_start(1000, 220)
    svg += f'''
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="0"><stop stop-color="#58a6ff"/><stop offset="1" stop-color="#a371f7"/></linearGradient></defs>
<rect x="1" y="1" width="998" height="218" rx="18" fill="none" stroke="{BORDER}"/>
<circle cx="44" cy="38" r="7" fill="#ff5f56"/><circle cx="68" cy="38" r="7" fill="#ffbd2e"/><circle cx="92" cy="38" r="7" fill="#27c93f"/>
<text x="128" y="44" class="muted" font-size="15">awizz@github: ~</text>
<text x="42" y="104" class="title" font-size="46">AWIZZ</text>
<rect x="42" y="121" width="360" height="3" rx="2" fill="url(#g)"/>
<text x="42" y="154" class="muted" font-size="17">systems • software • experiments</text>
<text x="42" y="190" class="blue" font-size="15">$ currently hacking on {escape(latest_name)}</text>
<text x="958" y="190" class="muted" text-anchor="end" font-size="13">{contribution_total} contributions · synced {datetime.now(timezone.utc):%Y-%m-%d}</text>
</svg>'''
    write("header.svg", svg)


def make_stack():
    w, h = 1000, 160
    svg = svg_start(w, h)
    svg += f'<rect x="1" y="1" width="998" height="158" rx="18" fill="none" stroke="{BORDER}"/>'
    x, y = 28, 35
    for tech in STACK:
        width = max(78, len(tech) * 9 + 26)
        if x + width > 970:
            x, y = 28, y + 52
        svg += f'<rect x="{x}" y="{y}" width="{width}" height="34" rx="9" fill="{CARD}" stroke="{BORDER}"/>'
        svg += f'<text x="{x + 13}" y="{y + 22}" fill="{TEXT}" font-size="13">{escape(tech)}</text>'
        x += width + 10
    svg += '</svg>'
    write("stack.svg", svg)


def make_stats(user, repos, total_contrib, current_streak, longest_streak):
    own = [r for r in repos if not r.get("fork") and r["name"].lower() != USER.lower()]
    stars = sum(r.get("stargazers_count", 0) for r in own)
    values = [
        (str(total_contrib), "contributions / year"),
        (str(len(own)), "public projects"),
        (str(user.get("followers", 0)), "followers"),
        (str(current_streak), "current streak"),
        (str(longest_streak), "longest streak"),
        (str(stars), "stars received"),
    ]
    svg = svg_start(1000, 205)
    svg += f'<rect x="1" y="1" width="998" height="203" rx="18" fill="none" stroke="{BORDER}"/>'
    for i, (value, label) in enumerate(values):
        col, row = i % 3, i // 3
        x, y = 44 + col * 320, 62 + row * 85
        svg += f'<text x="{x}" y="{y}" class="blue" font-size="30" font-weight="700">{escape(value)}</text>'
        svg += f'<text x="{x}" y="{y + 25}" class="muted" font-size="13">{escape(label)}</text>'
    svg += '</svg>'
    write("stats.svg", svg)


def make_languages(repos):
    totals = Counter()
    for repo in repos:
        if repo.get("fork") or repo.get("archived") or repo["name"].lower() == USER.lower():
            continue
        try:
            totals.update(api(f'/repos/{USER}/{repo["name"]}/languages'))
        except Exception as e:
            print(f"language fetch failed for {repo['name']}: {e}")
    top = totals.most_common(6)
    total = sum(v for _, v in top) or 1
    palette = ["#58a6ff", "#a371f7", "#3fb950", "#d29922", "#f778ba", "#79c0ff"]
    svg = svg_start(1000, 225)
    svg += f'<rect x="1" y="1" width="998" height="223" rx="18" fill="none" stroke="{BORDER}"/>'
    svg += f'<text x="34" y="42" class="title" font-size="18">language mix</text>'
    x = 34
    for idx, (lang, value) in enumerate(top):
        width = 932 * value / total
        svg += f'<rect x="{x:.1f}" y="64" width="{width:.1f}" height="15" fill="{palette[idx]}" rx="4"/>'
        x += width
    for idx, (lang, value) in enumerate(top):
        col, row = idx % 3, idx // 3
        x0, y0 = 42 + col * 305, 118 + row * 48
        pct = value / total * 100
        svg += f'<circle cx="{x0}" cy="{y0 - 5}" r="6" fill="{palette[idx]}"/>'
        svg += f'<text x="{x0 + 16}" y="{y0}" fill="{TEXT}" font-size="14">{escape(lang)}</text>'
        svg += f'<text x="{x0 + 190}" y="{y0}" class="muted" font-size="13">{pct:.1f}%</text>'
    svg += '</svg>'
    write("languages.svg", svg)


def make_contributions(weeks, total):
    level_colors = {
        "NONE": "#161b22", "FIRST_QUARTILE": "#0e4429", "SECOND_QUARTILE": "#006d32",
        "THIRD_QUARTILE": "#26a641", "FOURTH_QUARTILE": "#39d353",
    }
    cell, gap = 12, 4
    x0, y0 = 110, 76
    svg = svg_start(1000, 220)
    svg += f'<rect x="1" y="1" width="998" height="218" rx="18" fill="none" stroke="{BORDER}"/>'
    svg += f'<text x="34" y="40" class="title" font-size="18">contribution signal</text><text x="965" y="40" text-anchor="end" class="muted" font-size="13">{total} in the last year</text>'
    for wi, week in enumerate(weeks[-53:]):
        for di, day in enumerate(week["contributionDays"]):
            x, y = x0 + wi * (cell + gap), y0 + di * (cell + gap)
            color = level_colors.get(day["contributionLevel"], "#161b22")
            count = day["contributionCount"]
            svg += f'<rect x="{x}" y="{y}" width="{cell}" height="{cell}" rx="3" fill="{color}"><title>{day["date"]}: {count} contributions</title></rect>'
    svg += f'<text x="34" y="92" class="muted" font-size="12">Mon</text><text x="34" y="124" class="muted" font-size="12">Wed</text><text x="34" y="156" class="muted" font-size="12">Fri</text>'
    svg += f'<text x="110" y="199" class="muted" font-size="12">less</text>'
    for i, c in enumerate(["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]):
        svg += f'<rect x="{150 + i * 19}" y="189" width="12" height="12" rx="3" fill="{c}"/>'
    svg += f'<text x="252" y="199" class="muted" font-size="12">more</text></svg>'
    write("contributions.svg", svg)


def make_project(repo):
    name = repo["name"]
    desc = clamp(repo.get("description"), 92)
    lines = textwrap.wrap(desc, width=48)[:2] or ["No description yet."]
    lang = repo.get("language") or "mixed"
    updated = (repo.get("pushed_at") or "")[:10]
    svg = svg_start(480, 174)
    svg += f'<rect x="1" y="1" width="478" height="172" rx="18" fill="none" stroke="{BORDER}"/>'
    svg += f'<text x="25" y="40" class="blue" font-size="18" font-weight="700">{escape(name)}</text>'
    for i, line in enumerate(lines):
        svg += f'<text x="25" y="{75 + i*22}" fill="{TEXT}" font-size="13">{escape(line)}</text>'
    svg += f'<circle cx="31" cy="143" r="5" fill="{GREEN}"/><text x="44" y="148" class="muted" font-size="12">{escape(lang)}</text>'
    svg += f'<text x="455" y="148" text-anchor="end" class="muted" font-size="12">updated {escape(updated)}</text></svg>'
    write(f"project-{name}.svg", svg)


def main():
    user = api(f"/users/{USER}")
    repos = api(f"/users/{USER}/repos?per_page=100&type=owner&sort=updated")
    now = datetime.now(timezone.utc)
    start = now - timedelta(days=370)
    query = '''query($login:String!,$from:DateTime!,$to:DateTime!){user(login:$login){contributionsCollection(from:$from,to:$to){contributionCalendar{totalContributions weeks{contributionDays{date contributionCount contributionLevel}}}}}}'''
    cal = graphql(query, {"login": USER, "from": start.isoformat(), "to": now.isoformat()})["user"]["contributionsCollection"]["contributionCalendar"]
    weeks = cal["weeks"]
    days = [d for w in weeks for d in w["contributionDays"]]
    current, longest = streaks(days)

    make_header(user, repos, cal["totalContributions"])
    make_stack()
    make_stats(user, repos, cal["totalContributions"], current, longest)
    make_languages(repos)
    make_contributions(weeks, cal["totalContributions"])

    repo_by_name = {r["name"]: r for r in repos}
    for name in FEATURED:
        repo = repo_by_name.get(name) or api(f"/repos/{USER}/{name}")
        make_project(repo)

    print("profile assets generated")


if __name__ == "__main__":
    main()
