#!/usr/bin/env python3
"""Generates a self-hosted 'trophy case' SVG for the profile README, using
only the GitHub REST API. Avoids depending on third-party trophy widgets/
actions that go down or hit rate limits.

Env vars:
  GITHUB_TOKEN    - auth token (GITHUB_TOKEN secret is fine)
  GITHUB_USERNAME - profile username
  OUTPUT_PATH     - where to write the svg (default dist/trophy.svg)
"""

import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

TOKEN = os.environ["GITHUB_TOKEN"]
USERNAME = os.environ["GITHUB_USERNAME"]
OUTPUT_PATH = os.environ.get("OUTPUT_PATH", "dist/trophy.svg")

BG = "#0F0C29"
ACCENT = "#00F5D4"
TEXT = "#C9D1D9"
CARD_BG = "#181534"
RANK_COLORS = {
    "S": "#00F5D4",
    "A": "#7CFFCB",
    "B": "#8892B0",
    "C": "#5A5F73",
}


def api_get(url):
    req = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {TOKEN}",
            "Accept": "application/vnd.github+json",
            "User-Agent": f"{USERNAME}-profile-readme-bot",
        },
    )
    with urllib.request.urlopen(req) as resp:
        return json.load(resp)


def fetch_all_repos(username):
    repos = []
    page = 1
    while True:
        batch = api_get(
            f"https://api.github.com/users/{username}/repos"
            f"?per_page=100&page={page}&type=owner"
        )
        if not isinstance(batch, list) or not batch:
            break
        repos.extend(batch)
        if len(batch) < 100:
            break
        page += 1
    return repos


def rank_for(value, thresholds):
    """thresholds: list of (min_value, rank) sorted descending by min_value."""
    for min_value, rank in thresholds:
        if value >= min_value:
            return rank
    return "C"


def build_stats(username):
    user = api_get(f"https://api.github.com/users/{username}")
    repos = fetch_all_repos(username)

    owned_repos = [r for r in repos if not r.get("fork")]
    total_stars = sum(r.get("stargazers_count", 0) for r in owned_repos)
    total_forks = sum(r.get("forks_count", 0) for r in owned_repos)
    public_repos = user.get("public_repos", len(repos))
    followers = user.get("followers", 0)

    created_at = user.get("created_at")
    account_years = 0
    if created_at:
        created = datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ").replace(
            tzinfo=timezone.utc
        )
        account_years = (datetime.now(timezone.utc) - created).days // 365

    stats = [
        {
            "label": "Stars",
            "value": total_stars,
            "rank": rank_for(total_stars, [(200, "S"), (50, "A"), (10, "B")]),
        },
        {
            "label": "Followers",
            "value": followers,
            "rank": rank_for(followers, [(200, "S"), (50, "A"), (10, "B")]),
        },
        {
            "label": "Repositories",
            "value": public_repos,
            "rank": rank_for(public_repos, [(50, "S"), (20, "A"), (5, "B")]),
        },
        {
            "label": "Forks Received",
            "value": total_forks,
            "rank": rank_for(total_forks, [(100, "S"), (25, "A"), (5, "B")]),
        },
        {
            "label": "Account Age",
            "value": f"{account_years}y",
            "rank": rank_for(account_years, [(8, "S"), (4, "A"), (1, "B")]),
        },
    ]
    return stats


def render_svg(stats):
    card_w, card_h, gap = 150, 130, 16
    width = len(stats) * card_w + (len(stats) - 1) * gap + 20
    height = card_h + 20

    cards = []
    for i, s in enumerate(stats):
        x = 10 + i * (card_w + gap)
        y = 10
        rank_color = RANK_COLORS.get(s["rank"], RANK_COLORS["C"])
        cards.append(f'''
    <g transform="translate({x},{y})">
      <rect width="{card_w}" height="{card_h}" rx="12" fill="{CARD_BG}" stroke="{rank_color}" stroke-width="1.5"/>
      <text x="{card_w/2}" y="34" text-anchor="middle" font-family="Segoe UI, Verdana, sans-serif"
            font-size="13" fill="{TEXT}">{s["label"]}</text>
      <text x="{card_w/2}" y="72" text-anchor="middle" font-family="Segoe UI, Verdana, sans-serif"
            font-size="30" font-weight="700" fill="{ACCENT}">{s["value"]}</text>
      <text x="{card_w/2}" y="104" text-anchor="middle" font-family="Segoe UI, Verdana, sans-serif"
            font-size="13" font-weight="700" fill="{rank_color}">Rank {s["rank"]}</text>
    </g>''')

    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">
  <rect width="{width}" height="{height}" fill="{BG}"/>
  {"".join(cards)}
</svg>'''
    return svg


def main():
    stats = build_stats(USERNAME)
    svg = render_svg(stats)

    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(svg)

    print(f"Wrote {OUTPUT_PATH} with {len(stats)} stat cards.")


if __name__ == "__main__":
    sys.exit(main())