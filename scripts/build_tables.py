"""Build CSVs and README tables from data/ipos_raw.json (run after fetch_ipos.py)."""
import csv
import json
from datetime import date, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
raw = json.loads((ROOT / "data" / "ipos_raw.json").read_text())
ASOF = raw["meta"]["fetched_at_utc"][:10]
FIVE_Y = (date.fromisoformat(ASOF) - timedelta(days=5 * 365)).isoformat()
THREE_Y = (date.fromisoformat(ASOF) - timedelta(days=3 * 365)).isoformat()
TECH_SECTORS = {"Technology"}
TECH_INDUSTRIES = {"Internet Retail", "Internet Content & Information", "Electronic Gaming & Multimedia",
                   "Health Information Services", "Telecom Services"}


def f(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def row(r):
    issue = f(r["issue_price"])
    cur = f(r["current_nse"]) or f(r["current_bse"])
    op, cl = f(r["listing_open"]), f(r["listing_close"])
    band = f"{r['band_low']}-{r['band_high']}" if r["band_low"] else "Fixed"
    pct = lambda a: round((a / issue - 1) * 100, 1) if a and issue else None
    return {
        "company": r["company"].strip(), "symbol": r["symbol"] or "", "board": r["board"],
        "sector": r["sector"] or "Unclassified", "industry": r["industry"] or "Unclassified",
        "listing_date": r["listing_date"], "price_band": band, "issue_price": issue,
        "listing_open": op, "listing_close": cl, "listing_open_gain_pct": pct(op),
        "current_price": cur, "current_gain_pct": pct(cur),
    }


rows = sorted((row(r) for r in raw["rows"]), key=lambda x: (x["board"], x["sector"], x["industry"], x["listing_date"]))
cols = list(rows[0])


def write(name, rs):
    with open(ROOT / "data" / name, "w", newline="") as fh:
        w = csv.DictWriter(fh, cols)
        w.writeheader()
        w.writerows(rs)


main = [r for r in rows if r["board"] == "mainboard"]
sme = [r for r in rows if r["board"] == "sme"]
is_tech = lambda r: r["sector"] in TECH_SECTORS or r["industry"] in TECH_INDUSTRIES
tech5 = [r for r in rows if is_tech(r) and r["listing_date"] >= FIVE_Y]
write("mainboard.csv", main)
write("sme.csv", sme)
write("tech_last5y.csv", tech5)

n = lambda v: "-" if v is None else f"{v:g}"
pc = lambda v: "-" if v is None else f"{v:+.1f}%"


def table(rs, with_industry=True):
    h = "| Company | Listed | Price band | Issue | Listing open | Listing close | Current | Since issue |\n|---|---|---|---|---|---|---|---|\n"
    return h + "\n".join(
        f"| {r['company']} ({r['symbol'] or '-'}) | {r['listing_date']} | {r['price_band']} | {n(r['issue_price'])} | "
        f"{n(r['listing_open'])} | {n(r['listing_close'])} | {n(r['current_price'])} | {pc(r['current_gain_pct'])} |" for r in rs)


def grouped(rs):
    out, key = [], None
    for r in rs:
        if (r["sector"], r["industry"]) != key:
            key = (r["sector"], r["industry"])
            out.append(f"\n#### {r['sector']} / {r['industry']}\n")
            cur = []
            out.append(cur)
        cur.append(r)
    return "\n".join(x if isinstance(x, str) else table(x) for x in out)


md = [f"# Indian IPOs since 2021\n\nData as of **{ASOF}** (fetched {raw['meta']['fetched_at_utc']}). Prices in INR.\n"
      "Sources: Chittorgarh listing report + IPO pages (issue price, band, listing open/close, current price), "
      "Yahoo Finance (sector/industry). Current price = NSE, else BSE. 'Fixed' = fixed-price issue (no band). "
      "'Unclassified' = Yahoo has no profile (mostly SME and delisted/suspended names).\n",
      f"- Mainboard: {len(main)} listings. SME: {len(sme)} listings.\n- Full data: `data/mainboard.csv`, `data/sme.csv`, `data/tech_last5y.csv`.\n"
      f"\n## Tech-sector IPOs, last 5 years (listed since {FIVE_Y}): {len(tech5)}\n",
      "Tech = Yahoo sector Technology, or industry Internet/online retail, content, gaming, health information, telecom. "
      "Whether a company is a 'startup' is not in any data source; review this list.\n"]
for b in ("mainboard", "sme"):
    rs = [r for r in tech5 if r["board"] == b]
    md.append(f"\n### {b.upper()} tech ({len(rs)})\n\n{grouped(rs)}\n")
md.append(f"\n## All mainboard IPOs by industry ({len(main)})\n{grouped(main)}\n")
md.append(f"\n## SME IPOs\n\nToo large for this page ({len(sme)} rows): see `data/sme.csv`. Listed in last 3 years: "
          f"{sum(1 for r in sme if r['listing_date'] >= THREE_Y)}.\n")
(ROOT / "README.md").write_text("\n".join(md))
print(len(main), len(sme), len(tech5), sum(1 for r in tech5 if r['board']=='mainboard'))
