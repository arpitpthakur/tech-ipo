"""Collect Indian IPO listings (2021 onward) from Chittorgarh + Yahoo Finance into data/*.json.

Sources (all fetched at runtime, nothing typed from memory):
  - Chittorgarh listing report 25: issue price, listing open/close, current BSE/NSE price
  - Chittorgarh IPO detail page: price band
  - Yahoo Finance assetProfile: sector / industry
"""
import json
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from pathlib import Path

import requests

OUT = Path(__file__).resolve().parent.parent / "data"
API = "https://webnodejs.chittorgarh.com/cloud/report/data-read"
HDR = {"User-Agent": "Mozilla/5.0", "Referer": "https://www.chittorgarh.com/"}
YEARS = range(2021, 2027)
S = requests.Session()
S.headers.update(HDR)


def get(url, retries=4, **kw):
    for i in range(retries):
        try:
            r = S.get(url, timeout=40, **kw)
            if r.status_code == 200:
                return r
        except requests.RequestException:
            pass
        time.sleep(1.5 * (i + 1))
    return None


def listings(board, year):
    rows, page, seen = [], 1, set()
    while True:
        r = get(f"{API}/25/{page}/10/{year}/2026-27/0/{board}/all?search=")
        d = r.json() if r else {}
        chunk = [c for c in (d.get("reportTableData") or []) if c.get("~id") not in seen]
        if not chunk:
            return rows
        seen.update(c.get("~id") for c in chunk)
        rows += chunk
        page += 1


def clean(r, board):
    g = lambda k: r.get(k)
    return {
        "board": board, "company": g("Company"), "symbol": g("NSE Symbol"), "bse_code": g("BSE Scrip Code"),
        "isin": g("ISIN"), "listing_at": g("Listing At"), "open_date": g("~issue_open_date_plan"),
        "listing_date": (g("~IL_IPO_Listing_date") or "")[:10], "issue_price": g("Issue Price (Rs.)"),
        "listing_open": g("Open Price on Listing (Rs.)"), "listing_close": g("Close Price on Listing (Rs.)"),
        "current_bse": g("Current Price <br>at BSE (Rs.)"), "current_nse": g("Current Price <br>at NSE (Rs.)"),
        "slug": g("~urlrewrite_folder_name"), "id": g("~id"),
    }


def band(row):
    r = get(f"https://www.chittorgarh.com/ipo/{row['slug']}/{row['id']}/")
    m = re.search(r"Price Band\s*(?:</[^>]+>\s*<[^>]+>\s*)*₹?\s*([\d.,]+)\s*to\s*₹?\s*([\d.,]+)", r.text) if r else None
    if not m and r:
        t = re.sub(r"<[^>]+>", " ", r.text)
        m = re.search(r"Price Band\s*₹\s*([\d.,]+)\s*to\s*₹\s*([\d.,]+)", re.sub(r"\s+", " ", t))
    row["band_low"], row["band_high"] = (m.group(1).replace(",", ""), m.group(2).replace(",", "")) if m else (None, None)
    return row


def yahoo_session():
    y = requests.Session()
    y.headers.update({"User-Agent": "Mozilla/5.0"})
    y.get("https://fc.yahoo.com", timeout=20)
    crumb = y.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=20).text
    return y, crumb


def profile(row, y, crumb):
    sym = row.get("symbol")
    row["sector"] = row["industry"] = None
    if not sym:
        return row
    r = None
    for suffix in (".NS", ".BO"):
        code = sym if suffix == ".NS" else str(row.get("bse_code") or "")
        if not code:
            continue
        for _ in range(3):
            try:
                r = y.get(f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{code}{suffix}",
                          params={"modules": "assetProfile", "crumb": crumb}, timeout=30)
                if r.status_code in (200, 404):
                    break
            except requests.RequestException:
                pass
            time.sleep(1.5)
        if r is not None and r.status_code == 200:
            try:
                p = r.json()["quoteSummary"]["result"][0]["assetProfile"]
                row["sector"], row["industry"] = p.get("sectorDisp"), p.get("industryDisp")
                return row
            except (KeyError, TypeError, IndexError):
                pass
    return row


def main():
    OUT.mkdir(exist_ok=True)
    rows = []
    for board in ("mainboard", "sme"):
        for y in YEARS:
            chunk = [clean(r, board) for r in listings(board, y)]
            print(board, y, len(chunk), flush=True)
            rows += chunk
    seen, uniq = set(), []
    for r in rows:
        if r["id"] not in seen:
            seen.add(r["id"])
            uniq.append(r)
    with ThreadPoolExecutor(8) as ex:
        uniq = list(ex.map(band, uniq))
    ys, crumb = yahoo_session()
    with ThreadPoolExecutor(6) as ex:
        uniq = list(ex.map(lambda r: profile(r, ys, crumb), uniq))
    meta = {"fetched_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "sources": ["chittorgarh.com report 25 + IPO detail pages", "Yahoo Finance assetProfile"]}
    (OUT / "ipos_raw.json").write_text(json.dumps({"meta": meta, "rows": uniq}, indent=1))
    print("done", len(uniq), file=sys.stderr)


if __name__ == "__main__":
    main()
