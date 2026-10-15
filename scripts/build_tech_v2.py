import csv, json, time, datetime, requests
from concurrent.futures import ThreadPoolExecutor

ADD = "ZOMATO POLICYBZR GROWW EASEMYTRIP YATRA TBOTEK IXIGO KISSHT TURTLEMINT DELHIVERY SHADOWFAX RENTOMOJO PHYSICS LENSKART NAZARA CARTRADE LATENTVIEW FINO ARISINFRA PERNIASPOP".split()
ALIAS = {"ZOMATO": "ETERNAL"}
raw = {r["symbol"]: r for r in json.load(open("data/ipos_raw.json"))["rows"] if r["board"] == "mainboard"}
keep = {r["symbol"] for r in csv.DictReader(open("data/tech_last5y_validated.csv"))} | set(ADD)
rows = [r for r in csv.DictReader(open("data/mainboard.csv")) if r["symbol"] in keep]

y = requests.Session(); y.headers.update({"User-Agent": "Mozilla/5.0"})
y.get("https://fc.yahoo.com", timeout=20)
crumb = y.get("https://query1.finance.yahoo.com/v1/test/getcrumb", timeout=20).text
MODS = "assetProfile,financialData,summaryDetail,price,defaultKeyStatistics"

def get(url, **p):
    for _ in range(3):
        try:
            r = y.get(url, params=p, timeout=30)
            if r.status_code == 200: return r.json()
            if r.status_code == 404: return None
        except requests.RequestException: pass
        time.sleep(1.5)

def pull(r):
    sym = r["symbol"]; out = {"symbol": sym}
    codes = [ALIAS.get(sym, sym) + ".NS"]
    if raw[sym].get("bse_code"): codes.append(f"{raw[sym]['bse_code']}.BO")
    for c in codes:
        q = get(f"https://query1.finance.yahoo.com/v10/finance/quoteSummary/{c}", modules=MODS, crumb=crumb)
        if q and q["quoteSummary"]["result"]:
            res = q["quoteSummary"]["result"][0]
            raw_v = lambda d, k: (d.get(k) or {}).get("raw") if isinstance(d.get(k), dict) else d.get(k)
            ap, fd, pr = res.get("assetProfile", {}), res.get("financialData", {}), res.get("price", {})
            out.update(code=c, summary=ap.get("longBusinessSummary"), employees=ap.get("fullTimeEmployees"), website=ap.get("website"),
                       sector=ap.get("sectorDisp"), industry=ap.get("industryDisp"),
                       revenue=raw_v(fd, "totalRevenue"), ebitda=raw_v(fd, "ebitda"), net_margin=raw_v(fd, "profitMargins"),
                       rev_growth=raw_v(fd, "revenueGrowth"), cash=raw_v(fd, "totalCash"), debt=raw_v(fd, "totalDebt"),
                       op_margin=raw_v(fd, "operatingMargins"), roe=raw_v(fd, "returnOnEquity"), target=raw_v(fd, "targetMeanPrice"),
                       rec=fd.get("recommendationKey"), mcap=raw_v(pr, "marketCap"), price=raw_v(pr, "regularMarketPrice"))
            ch = get(f"https://query1.finance.yahoo.com/v8/finance/chart/{c}", range="10y", interval="1mo", events="split")
            ev = ((ch or {}).get("chart", {}).get("result") or [{}])[0].get("events", {}).get("splits", {})
            out["splits"] = [(datetime.datetime.fromtimestamp(v["date"]).strftime("%Y-%m-%d"), v["numerator"] / v["denominator"]) for v in ev.values()]
            break
    return out

with ThreadPoolExecutor(6) as ex: res = list(ex.map(pull, rows))
json.dump({r["symbol"]: r for r in res}, open("data/profiles.json", "w"))
print(len(res), "pulled;", sum(1 for r in res if "code" not in r), "no Yahoo data;", sum(1 for r in res if r.get("summary")), "with summary")
print([r["symbol"] for r in res if "code" not in r])
