"""Render a static preview of the proposed one-page Power BI layout."""
from pathlib import Path

import pandas as pd
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data/processed"
DEST = ROOT / "dashboard/preview.png"
W, H = 1600, 900
BG, PANEL, BORDER = "#0b1424", "#13243a", "#274059"
WHITE, MUTED, TEAL, GOLD, RED = "#f3f7fc", "#9bb0c5", "#45d1c1", "#f6ba68", "#f17682"


def font(size, bold=False):
    path = Path("C:/Windows/Fonts/seguisb.ttf" if bold else "C:/Windows/Fonts/segoeui.ttf")
    return ImageFont.truetype(str(path), size)


def box(draw, xy, radius=18):
    draw.rounded_rectangle(xy, radius=radius, fill=PANEL, outline=BORDER, width=2)


def text(draw, xy, value, size=20, color=WHITE, bold=False):
    draw.text(xy, str(value), font=font(size, bold), fill=color)


def line_chart(draw, values, xy, color, baseline=None):
    x0, y0, x1, y1 = xy
    values = list(values)
    lo = min(values + ([baseline] if baseline is not None else []))
    hi = max(values + ([baseline] if baseline is not None else []))
    if hi == lo:
        hi += 1
    pad = (hi - lo) * .08
    lo -= pad
    hi += pad
    if baseline is not None:
        y = y1 - (baseline - lo) / (hi - lo) * (y1 - y0)
        draw.line([(x0, y), (x1, y)], fill=BORDER, width=2)
    pts = [(x0 + i * (x1 - x0) / max(1, len(values) - 1),
            y1 - (v - lo) / (hi - lo) * (y1 - y0)) for i, v in enumerate(values)]
    draw.line(pts, fill=color, width=4, joint="curve")
    for x, y in [pts[0], pts[-1]]:
        draw.ellipse((x-5, y-5, x+5, y+5), fill=color)


def main():
    prices = pd.read_csv(DATA / "prices.csv", parse_dates=["trade_date"])
    issues = pd.read_csv(DATA / "quality_issues.csv")
    monthly = pd.read_csv(DATA / "backtest_monthly.csv")
    metrics = pd.read_csv(DATA / "backtest_metrics.csv").set_index("strategy")
    actions = pd.read_csv(DATA / "corporate_actions.csv")
    image = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(image)

    text(draw, (54, 32), "Equity data quality and momentum", 38, WHITE, True)
    text(draw, (56, 82), "FTSE large-cap sample  ·  18 Oct 2021–16 Oct 2026  ·  GBX", 20, MUTED)
    cards = [
        (54, "20", "Securities"), (430, f"{len(prices):,}", "Price rows"),
        (806, str(len(issues)), "Quality flags"), (1182, "48", "Backtest months"),
    ]
    for x, value, label in cards:
        box(draw, (x, 128, x+350, 240))
        text(draw, (x+24, 148), value, 38, TEAL, True)
        text(draw, (x+24, 201), label, 18, MUTED)

    box(draw, (54, 262, 782, 545))
    text(draw, (80, 283), "AstraZeneca adjusted close", 23, WHITE, True)
    text(draw, (80, 316), "Monthly last price (GBX)", 17, MUTED)
    azn = prices.loc[prices.ticker.eq("AZN.L")].set_index("trade_date")["adj_close"].resample("ME").last().dropna()
    line_chart(draw, azn.values, (92, 363, 745, 493), TEAL)
    text(draw, (91, 501), "Oct 2021", 16, MUTED)
    text(draw, (662, 501), "Oct 2026", 16, MUTED)

    box(draw, (806, 262, 1546, 545))
    text(draw, (832, 283), "Quality issue mix", 23, WHITE, True)
    counts = issues.issue_type.value_counts()
    labels = [("Missing peer days", int(counts.get("missing_peer_day", 0)), GOLD),
              ("Raw jumps >20%", int(counts.get("raw_jump_gt_20pct", 0)), RED),
              ("Adjusted jumps >20%", int(counts.get("adjusted_jump_gt_20pct", 0)), TEAL),
              ("Duplicates / invalid", int(counts.get("duplicate_row", 0) + counts.get("invalid_price", 0)), MUTED)]
    for idx, (label, count, color) in enumerate(labels):
        y = 338 + idx * 45
        text(draw, (833, y), label, 18, MUTED)
        draw.rounded_rectangle((1070, y+2, 1467, y+20), radius=8, fill="#24394d")
        if count:
            draw.rounded_rectangle((1070, y+2, 1070+397*count/max(10, max(counts)), y+20), radius=8, fill=color)
        text(draw, (1480, y-3), count, 21, WHITE, True)

    box(draw, (54, 568, 1012, 824))
    text(draw, (80, 590), "Growth of 1 invested", 23, WHITE, True)
    text(draw, (80, 623), "Monthly rebalanced · adjusted close", 17, MUTED)
    draw.line((698, 608, 730, 608), fill=TEAL, width=5)
    text(draw, (742, 594), "Top five", 18, MUTED)
    draw.line((859, 608, 891, 608), fill=GOLD, width=5)
    text(draw, (902, 594), "Equal weight", 18, MUTED)
    combined = list(monthly.momentum_wealth) + list(monthly.benchmark_wealth) + [1]
    lo, hi = min(combined), max(combined)
    def plot(series, color):
        values = [1] + list(series)
        pts = [(84+i*895/(len(values)-1), 782-(v-lo)/(hi-lo)*125) for i,v in enumerate(values)]
        draw.line(pts, fill=color, width=4)
    plot(monthly.benchmark_wealth, GOLD)
    plot(monthly.momentum_wealth, TEAL)
    text(draw, (85, 788), "Oct 2022", 16, MUTED)
    text(draw, (920, 788), "Oct 2026", 16, MUTED)

    box(draw, (1036, 568, 1546, 824))
    text(draw, (1062, 590), "Backtest summary", 23, WHITE, True)
    m, b = metrics.loc["momentum"], metrics.loc["benchmark"]
    headers = ["", "Top five", "Equal weight"]
    for x, label in zip([1062, 1290, 1425], headers):
        text(draw, (x, 632), label, 16, MUTED)
    rows = [("Total return", "total_return"), ("Ann. volatility", "annualized_volatility"),
            ("Max drawdown", "max_drawdown")]
    for i, (label, col) in enumerate(rows):
        y = 672 + i*42
        text(draw, (1062, y), label, 18, MUTED)
        text(draw, (1290, y), f"{m[col]:.1%}", 19, TEAL, True)
        text(draw, (1425, y), f"{b[col]:.1%}", 19, GOLD, True)

    text(draw, (55, 844), f"Events: {(actions.action_type=='dividend').sum()} dividends · {(actions.action_type=='split').sum()} splits/consolidations  |  Present-day universe; illustrative, no costs", 17, MUTED)
    DEST.parent.mkdir(parents=True, exist_ok=True)
    image.save(DEST)
    print(DEST)


if __name__ == "__main__":
    main()
