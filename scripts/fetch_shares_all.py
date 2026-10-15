import json, requests
from concurrent.futures import ThreadPoolExecutor
raw = {r["id"]: r for r in json.load(open("data/ipos_raw.json"))["rows"] if r["board"] == "mainboard"}
yp = json.load(open("data/yahoo_prices.json"))
y = requests.Session(); y.headers.update({"User-Agent": "Mozilla/5.0"}); y.get("https://fc.yahoo.com", timeout=20)
crumb = y.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=20).text
def f(i):
    c = yp.get(str(i), {}).get("code")
    if not c: return str(i), None
    try:
        res = y.get(f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{c}", params={"modules": "defaultKeyStatistics,price", "crumb": crumb}, timeout=30).json()["quoteSummary"]["result"][0]
        g = lambda d, k: (d.get(k) or {}).get("raw") if isinstance(d.get(k), dict) else d.get(k)
        return str(i), dict(shares=g(res["defaultKeyStatistics"], "sharesOutstanding") or g(res["price"], "sharesOutstanding"), eps=g(res["defaultKeyStatistics"], "trailingEps"), bvps=g(res["defaultKeyStatistics"], "bookValue"))
    except Exception:
        return str(i), None
with ThreadPoolExecutor(6) as ex: out = dict(ex.map(f, raw))
json.dump(out, open("data/all_shares.json", "w"))
print(sum(1 for v in out.values() if v and v.get("shares")), "with shares of", len(out))
