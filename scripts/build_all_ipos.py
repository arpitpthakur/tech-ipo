import csv, json, re, datetime
TODAY = datetime.date(2026, 10, 15)
fl = lambda x: float(x) if x not in (None, "", "None") else None

raw = json.load(open("data/ipos_raw.json"))["rows"]
rid = {(r["board"], r["company"]): r["id"] for r in raw}
rawid = {r["id"]: r for r in raw}
YP = json.load(open("data/yahoo_prices.json"))
DESC = json.load(open("data/descriptions.json"))
SH = json.load(open("data/all_shares.json"))
TECH_MB = {r["symbol"]: r for r in csv.DictReader(open("data/tech_mainboard_v2.csv"))}
TECH_SM = {r["company"]: r for r in csv.DictReader(open("data/sme_tech_last5y.csv"))}
SHARES_TECH = json.load(open("data/shares_outstanding.json"))

SECTORS = [
 ("Financial Services", r"finance|nbfc|lending|\bloan|\bbank|insurance|broking|wealth|asset management|microfinance|stock broker|credit"),
 ("Pharma & Healthcare", r"pharma|drug|medicine|hospital|diagnostic|healthcare|medical|surgical|nutraceutical|ayurved|clinic|api manufactur|formulation"),
 ("Auto & Components", r"\bauto\b|automobile|automotive|vehicle|tyre|two-wheeler|electric vehicle|\bev\b"),
 ("Chemicals & Agri-inputs", r"chemical|pigment|dye|polymer|fertili[sz]er|agro ?chem|pesticide|paint|plastic|resin|packaging|adhesive|rubber"),
 ("Textiles & Apparel", r"textile|yarn|fabric|garment|apparel|cotton|denim|knit|saree|hosiery|embroider|spinning"),
 ("Food & Agri", r"\bfood|rice|flour|spice|\btea\b|dairy|edible|sugar|snack|bakery|beverage|fruit|seeds|\bfish|\bmeat|poultry|grain|agri|restaurant|coffee"),
 ("Construction, Infra & Real Estate", r"construction|infrastructure|\bepc\b|\broad|real estate|housing|developer|cement|builder|civil|bridge|realty|residential|tiles|ceramic|sanitary|granite|marble"),
 ("Metals & Engineering", r"steel|metal|iron|alloy|casting|forging|engineering|machinery|equipment|fabricat|pipes|wire|alumin|copper|bearing|valve|pump|tools|fasteners|manufactur"),
 ("Energy & Power", r"solar|power|renewable|energy|petroleum|biofuel|oil and gas|\boil\b|\bgas\b|transformer|battery|wind"),
 ("Electricals & Electronics", r"electrical|electronic|cable|switchgear|\bled\b|lighting|semiconductor|appliance"),
 ("Retail & Consumer", r"retail|jewel|furniture|footwear|cosmetic|consumer|e-?commerce|stores|apparel brand|lifestyle|handicraft|toys|personal care|home decor"),
 ("Logistics & Shipping", r"logistic|shipping|transport|freight|cargo|warehouse|courier|aviation|airline|ports?\b"),
 ("Hospitality & Travel", r"hotel|resort|travel|\btour|hospitality|tourism"),
 ("Education & Media", r"education|school|training|media|publishing|entertainment|film|advertis|broadcast"),
]
FALLBACK = {"Industrials": "Metals & Engineering", "Basic Materials": "Metals & Engineering", "Consumer Cyclical": "Retail & Consumer",
    "Consumer Defensive": "Food & Agri", "Healthcare": "Pharma & Healthcare", "Financial Services": "Financial Services",
    "Real Estate": "Construction, Infra & Real Estate", "Utilities": "Energy & Power", "Energy": "Energy & Power",
    "Communication Services": "Education & Media", "Technology": "Electricals & Electronics"}
def sector_from_desc(text, yahoo_sector=None):
    t = (text or "").lower()
    for name, pat in SECTORS:
        if re.search(pat, t): return name
    return FALLBACK.get(yahoo_sector, "Other / diversified")

rows = []
for board, fn in (("mainboard", "data/mainboard.csv"), ("sme", "data/sme.csv")):
    for r in csv.DictReader(open(fn)):
        i = rid.get((board, r["company"]))
        desc = DESC.get(str(i)) or ""
        sym = r["symbol"]
        tech = None
        if board == "mainboard" and sym in TECH_MB: tech = TECH_MB[sym]
        if board == "sme" and r["company"] in TECH_SM: tech = TECH_SM[r["company"]]
        iss, op = fl(r["issue_price"]), fl(r["listing_open"])
        chitt = fl(r["current_price"])
        y = YP.get(str(i), {})
        yprice = y.get("price") if "price" in y else None
        price, psrc, fac = chitt, "Chittorgarh", 1.0
        if tech is not None:
            price = fl(tech["now"] if board == "mainboard" else tech["current_price"])
            psrc = {"kite": "Zerodha Kite", "web": "web quote"}.get(tech["price_src"], "Chittorgarh")
            fac = fl(tech["split_factor"]) or 1.0
        elif yprice and (not chitt or 0.5 <= yprice / chitt <= 2.0):
            price, psrc = yprice, "Yahoo Finance"
        if tech is None and y.get("verified"):
            for d, ratio in y.get("splits", []):
                if d > r["listing_date"]: fac *= ratio
        mult = (price * fac / iss) if price and iss else None
        yrs = (TODAY - datetime.date.fromisoformat(r["listing_date"])).days / 365.25
        industry = r["industry"]
        if tech is not None:
            sector, ssrc = "Technology", "tech list"
            if board == "mainboard": industry = tech["industry"]
        else:
            sector = sector_from_desc(f"{industry} {desc[:300]}", r["sector"] if r["sector"] != "Unclassified" else None)
            ssrc = "from industry and business description"
        mc = None
        if board == "mainboard":
            if sym in SHARES_TECH: shares = SHARES_TECH[sym]["shares"]
            else: shares = (SH.get(str(i)) or {}).get("shares")
            if shares and price: mc = round(shares * price / 1e7)
        rows.append(dict(id=i, n=re.sub(r" (Ltd\.|Limited)$", "", r["company"]), s=sym, bd=board, d=r["listing_date"], b=r["price_band"], i=iss, o=op,
            lg=round((op / iss - 1) * 100, 1) if op and iss else None, c=price, ps=psrc, x=round(mult, 2) if mult else None,
            g=round((mult - 1) * 100, 1) if mult else None, y=round((mult ** (1 / yrs) - 1) * 100, 1) if mult and mult > 0 and yrs >= 1 else "",
            sec=sector, ind=industry, ss=ssrc, tech=tech is not None, mc=mc, about=desc[:520], adj=fac != 1.0))
json.dump(rows, open("data/all_ipos.json", "w"), ensure_ascii=False)
w = csv.DictWriter(open("data/all_ipos.csv", "w"), fieldnames=[k for k in rows[0] if k != "about"], extrasaction="ignore"); w.writeheader(); w.writerows(rows)
print(len(rows), "rows;", sum(r["tech"] for r in rows), "tech;", sum(1 for r in rows if r["g"] is None), "without gain")
