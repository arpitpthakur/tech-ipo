import csv, json, datetime
TODAY = datetime.date(2026, 10, 15)
P = json.load(open("data/profiles.json"))
tags = {r["symbol"]: r["startup_tag"] for r in csv.DictReader(open("data/startup_tags.csv"))}
IND_FIX = {"PHYSICS": "Education Services", "FINO": "Payments Bank / Fintech", "ARISINFRA": "Construction Materials Platform"}
KITE = json.load(open("data/kite_ltp.json"))["mainboard"]
prev = {r["symbol"]: r for r in csv.DictReader(open("data/tech_last5y_validated.csv"))}
fl = lambda x: float(x) if x not in (None, "") else None
out = []
for r in csv.DictReader(open("data/mainboard.csv")):
    s = r["symbol"]
    if s not in P: continue
    p = P[s]; iss, op, cur = fl(r["issue_price"]), fl(r["listing_open"]), fl(r["current_price"])
    price_src = "kite" if s in KITE else "chittorgarh"
    cur = KITE.get(s, cur)
    fac = 1
    for d, x in p.get("splits", []):
        if d > r["listing_date"]: fac *= x
    adj_now = cur * fac
    yrs = (TODAY - datetime.date.fromisoformat(r["listing_date"])).days / 365.25
    mult = adj_now / iss
    out.append(dict(symbol=s, company=r["company"], industry=IND_FIX.get(s) or prev.get(s, {}).get("industry") or p.get("industry") or r["industry"],
        listed=r["listing_date"], band=r["price_band"], issue=iss, listing_open=op, listing_gain=round((op / iss - 1) * 100, 1),
        now=cur, price_src=price_src, split_factor=fac, multiple=round(mult, 2), total_gain=round((mult - 1) * 100, 1),
        cagr=round((mult ** (1 / yrs) - 1) * 100, 1) if yrs >= 1 else "", years=round(yrs, 2), tag=tags[s]))
out.sort(key=lambda r: r["listed"])
w = csv.DictWriter(open("data/tech_mainboard_v2.csv", "w"), fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
print(len(out), "rows"); z = [r for r in out if r["symbol"] == "ZOMATO"][0]; print(z)
