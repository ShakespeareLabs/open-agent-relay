from __future__ import annotations

import csv
import sys
from pathlib import Path


def load_campaigns() -> list[dict[str, str]]:
    path = Path(__file__).with_name("campaigns.csv")
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def main() -> None:
    request = sys.stdin.read().strip()
    campaigns = load_campaigns()
    selected = [row for row in campaigns if row["campaign"].lower() in request.lower()]
    rows = selected or campaigns
    spend = sum(float(row["spend"]) for row in rows)
    revenue = sum(float(row["revenue"]) for row in rows)
    conversions = sum(int(row["conversions"]) for row in rows)
    return_on_ad_spend = revenue / spend if spend else 0
    cost_per_conversion = spend / conversions if conversions else 0
    scope = ", ".join(row["campaign"] for row in rows)
    print(f"Campaigns: {scope}")
    print(f"Spend: ${spend:,.2f}")
    print(f"Revenue: ${revenue:,.2f}")
    print(f"Conversions: {conversions}")
    print(f"ROAS: {return_on_ad_spend:.2f}x")
    print(f"Cost per conversion: ${cost_per_conversion:,.2f}")


if __name__ == "__main__":
    main()
