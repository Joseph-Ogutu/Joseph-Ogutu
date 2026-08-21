"""
Self-hosted replacement for streak-stats.demolab.com and
github-readme-activity-graph.vercel.app.

Pulls contribution data directly from GitHub's GraphQL API and renders
two clean SVG cards. No third-party services, no rate-limit surprises.
"""

import os
from datetime import date, datetime, timedelta

import requests

USERNAME = os.environ["GH_USERNAME"]
TOKEN = os.environ["GH_TOKEN"]

QUERY = """
query($userName: String!) {
  user(login: $userName) {
    contributionsCollection {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
          }
        }
      }
    }
  }
}
"""


def fetch_contributions():
    resp = requests.post(
        "https://api.github.com/graphql",
        json={"query": QUERY, "variables": {"userName": USERNAME}},
        headers={"Authorization": f"bearer {TOKEN}"},
        timeout=30,
    )
    resp.raise_for_status()
    data = resp.json()
    if "errors" in data:
        raise RuntimeError(f"GitHub GraphQL API returned errors: {data['errors']}")

    calendar = data["data"]["user"]["contributionsCollection"]["contributionCalendar"]
    days = []
    for week in calendar["weeks"]:
        for d in week["contributionDays"]:
            days.append((d["date"], d["contributionCount"]))
    days.sort()
    return days, calendar["totalContributions"]


def compute_streaks(days):
    counts_by_date = {
        datetime.strptime(d, "%Y-%m-%d").date(): c for d, c in days
    }
    all_dates = sorted(counts_by_date.keys())
    if not all_dates:
        return 0, 0

    today = date.today()
    cursor = today
    # today may legitimately still show 0 if the day isn't over yet —
    # don't let that alone zero out an active streak
    if counts_by_date.get(today, 0) == 0:
        cursor = today - timedelta(days=1)

    current_streak = 0
    while counts_by_date.get(cursor, 0) > 0:
        current_streak += 1
        cursor -= timedelta(days=1)

    longest_streak = 0
    running = 0
    for d in all_dates:
        if counts_by_date[d] > 0:
            running += 1
            longest_streak = max(longest_streak, running)
        else:
            running = 0

    return current_streak, longest_streak


def generate_stats_svg(total, current_streak, longest_streak):
    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='495' height='195' viewBox='0 0 495 195'>
  <rect width='495' height='195' rx='10' fill='#0D1117' stroke='#30363D'/>
  <text x='247' y='45' text-anchor='middle' fill='#58A6FF' font-family='Segoe UI, Ubuntu, sans-serif' font-size='18' font-weight='bold'>{USERNAME}'s Contribution Streak</text>
  <line x1='40' y1='70' x2='455' y2='70' stroke='#30363D'/>

  <text x='105' y='125' text-anchor='middle' fill='#F0F6FC' font-family='Segoe UI, Ubuntu, sans-serif' font-size='34' font-weight='bold'>{total}</text>
  <text x='105' y='150' text-anchor='middle' fill='#8B949E' font-family='Segoe UI, Ubuntu, sans-serif' font-size='12'>Total Contributions</text>

  <line x1='215' y1='90' x2='215' y2='160' stroke='#30363D'/>
  <text x='247' y='125' text-anchor='middle' fill='#F79000' font-family='Segoe UI, Ubuntu, sans-serif' font-size='34' font-weight='bold'>{current_streak}</text>
  <text x='247' y='150' text-anchor='middle' fill='#8B949E' font-family='Segoe UI, Ubuntu, sans-serif' font-size='12'>Current Streak</text>

  <line x1='325' y1='90' x2='325' y2='160' stroke='#30363D'/>
  <text x='390' y='125' text-anchor='middle' fill='#F0F6FC' font-family='Segoe UI, Ubuntu, sans-serif' font-size='34' font-weight='bold'>{longest_streak}</text>
  <text x='390' y='150' text-anchor='middle' fill='#8B949E' font-family='Segoe UI, Ubuntu, sans-serif' font-size='12'>Longest Streak</text>
</svg>"""


def generate_activity_svg(days, num_days=90):
    recent = days[-num_days:]
    counts = [c for _, c in recent]
    max_count = max(counts) if counts and max(counts) > 0 else 1

    width, height = 700, 200
    chart_top, chart_bottom = 40, 170
    chart_height = chart_bottom - chart_top
    bar_slot = (width - 40) / len(recent)

    bars = ""
    for i, (_, c) in enumerate(recent):
        bar_height = (c / max_count) * chart_height if c else 0
        x = 20 + i * bar_slot
        y = chart_bottom - bar_height
        color = "#39D353" if c > 0 else "#161B22"
        bars += (
            f"<rect x='{x:.1f}' y='{y:.1f}' "
            f"width='{bar_slot * 0.7:.1f}' height='{max(bar_height, 1):.1f}' "
            f"fill='{color}'/>"
        )

    return f"""<svg xmlns='http://www.w3.org/2000/svg' width='{width}' height='{height}' viewBox='0 0 {width} {height}'>
  <rect width='{width}' height='{height}' fill='#0D1117'/>
  <text x='20' y='25' fill='#58A6FF' font-family='Segoe UI, Ubuntu, sans-serif' font-size='16' font-weight='bold'>Last {num_days} Days of Activity</text>
  <line x1='20' y1='{chart_bottom}' x2='{width - 20}' y2='{chart_bottom}' stroke='#30363D'/>
  {bars}
</svg>"""


def main():
    days, total = fetch_contributions()
    current_streak, longest_streak = compute_streaks(days)

    os.makedirs("assets", exist_ok=True)
    with open("assets/streak-stats.svg", "w") as f:
        f.write(generate_stats_svg(total, current_streak, longest_streak))
    with open("assets/activity-graph.svg", "w") as f:
        f.write(generate_activity_svg(days))

    print(f"Total: {total} | Current streak: {current_streak} | Longest streak: {longest_streak}")


if __name__ == "__main__":
    main()