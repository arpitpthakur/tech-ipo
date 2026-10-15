import json, subprocess, datetime
from concurrent.futures import ThreadPoolExecutor

raw = json.load(open("data/ipos_raw.json"))["rows"]

def chart(code):
    out = subprocess.run(["curl", "-s", "-m", "25", "-A", "Mozilla/5.0",
        f"https://query1.finance.yahoo.com/v8/finance/chart/{code}?range=10y&interval=1mo&events=split"], capture_output=True, text=True).stdout
    try:
        res = json.loads(out)["chart"]["result"][0]
    except Exception:
        return None
    m = res["meta"]
    ev = res.get("events", {}).get("splits", {})
    return dict(code=code, price=m.get("regularMarketPrice"), first=m.get("firstTradeDate"),
                splits=[(datetime.datetime.fromtimestamp(v["date"]).strftime("%Y-%m-%d"), v["numerator"] / v["denominator"]) for v in ev.values()])

def ok(c, listing):
    if not c or c["price"] is None: return False
    if c["first"] is None: return True
    first = datetime.date.fromtimestamp(c["first"])
    return abs((first - datetime.date.fromisoformat(listing)).days) <= 60

def get(r):
    cands = []
    if r.get("symbol"): cands.append(f"{r['symbol']}.NS")
    if r.get("bse_code"): cands.append(f"{r['bse_code']}.BO")
    if r.get("symbol"): cands.append(f"{r['symbol']}.BO")
    tried = []
    for code in cands:
        c = chart(code)
        if c: tried.append(c)
        if ok(c, r["listing_date"]):
            c["verified"] = c["first"] is not None
            return r["id"], c
    return r["id"], {"rejected": [(t["code"], t["price"]) for t in tried]}

with ThreadPoolExecutor(10) as ex:
    res = dict(ex.map(get, raw))
json.dump(res, open("data/yahoo_prices.json", "w"))
good = [v for v in res.values() if "price" in v]
print(len(res), "rows;", len(good), "matched;", sum(1 for v in good if v.get("verified")), "verified by first-trade date")
