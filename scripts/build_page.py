import csv, json, re, sys, glob
OUT = sys.argv[1]
P = json.load(open("data/profiles.json"))
desc = json.load(open("data/descriptions.json"))
raw = {r["symbol"]: r for r in json.load(open("data/ipos_raw.json"))["rows"] if r["board"] == "mainboard"}
fl = lambda x: float(x) if x not in (None, "") else None

def inr(v):
    if v is None: return None
    c = v / 1e7
    if abs(c) >= 100000: return f"₹{c/100000:,.2f} lakh cr"
    return f"₹{c:,.0f} cr"

def trim(t, n=620):
    if not t: return ""
    t = re.sub(r"\s+", " ", t).strip()
    if len(t) <= n: return t
    cut = t[:n]; i = max(cut.rfind(". "), cut.rfind("; "))
    return (cut[:i + 1] if i > 250 else cut.rsplit(" ", 1)[0] + "…")

def perf_read(r):
    b = []
    m, yrs = r["multiple"], r["years"]
    s = f"IPO price ₹{r['issue']:g}, now ₹{r['now']:g}: {m:.1f}x the IPO price ({r['total_gain']:+,.0f}%)"
    if r["cagr"] != "": s += f", about {r['cagr']:.0f}% a year over {yrs:.1f} years"
    else: s += f", only {yrs*12:.0f} months since listing"
    b.append(s + ".")
    ratio = r["multiple"] / (r["listing_open"] / r["issue"]) if r["listing_open"] else None
    if ratio and r["listing_gain"] >= 15 and ratio < 1:
        b.append(f"Listed {r['listing_gain']:.0f}% above issue, but is now {abs(ratio-1)*100:.0f}% below the listing-day open. Buyers on day one are losing money.")
    elif ratio and r["listing_gain"] >= 15:
        b.append(f"Listed {r['listing_gain']:.0f}% above issue and has held it, now {(ratio-1)*100:+.0f}% from the listing-day open.")
    elif ratio and r["listing_gain"] < 5 and r["multiple"] > 1.2:
        b.append(f"Listed flat ({r['listing_gain']:+.0f}%), so the whole gain came after listing.")
    elif r["multiple"] < 1:
        b.append("Trades below the IPO price.")
    return b

def fin_read(p, now, mc):
    b = []
    g, nm, om, rev = p.get("rev_growth"), p.get("net_margin"), p.get("op_margin"), p.get("revenue")
    if g is not None:
        b.append("Latest-quarter revenue " + (f"grew {g*100:.0f}% year on year" + (", fast growth." if g > .3 else ".") if g >= 0 else f"fell {abs(g)*100:.0f}% year on year."))
    if nm is not None:
        if nm < -0.001: b.append(f"Loss-making: net margin {nm*100:.1f}% on trailing revenue.")
        elif nm < 0.05: b.append(f"Thin profit: net margin {nm*100:.1f}%.")
        else: b.append(f"Profitable: net margin {nm*100:.1f}%" + (f", operating margin {om*100:.1f}%." if om is not None else "."))
    cash, debt = p.get("cash"), p.get("debt")
    if cash is not None and debt is not None:
        b.append(f"Cash {inr(cash)} against debt {inr(debt)}: " + ("net cash." if cash >= debt else "more debt than cash."))
    if mc and rev and rev > 0:
        b.append(f"Market cap is {mc/rev:.1f}x trailing revenue.")
    t, pr = p.get("target"), now
    if t and pr:
        b.append(f"Analyst mean target ₹{t:,.0f} is {(t/pr-1)*100:+.0f}% from the current price" + (f" (consensus: {p['rec'].replace('_',' ')})." if p.get("rec") else "."))
    return b

VI = json.load(open("data/valuation_inputs.json"))
SH = json.load(open("data/shares_outstanding.json"))

def vtag(pe, loss):
    if loss: return "Loss-making"
    if pe is None: return None
    return "Cheap" if pe < 15 else "Fair" if pe <= 40 else "Rich"

NOTES = {}
for f in sorted(glob.glob("data/research/notes_*.json")): NOTES.update(json.load(open(f)))
rows = list(csv.DictReader(open("data/tech_mainboard_v2.csv")))
mb = []
for r in rows:
    for k in ("issue","listing_open","listing_gain","now","multiple","total_gain","years"): r[k] = float(r[k])
    r["cagr"] = float(r["cagr"]) if r["cagr"] != "" else ""
    p = P[r["symbol"]]
    sh = SH.get(r["symbol"]); mc = sh["shares"] * r["now"] if sh else None
    note = NOTES[r["symbol"]]
    vi = VI.get(r["symbol"], {}); eps, bv = vi.get("eps"), vi.get("bvps")
    pe = round(r["now"] / eps, 1) if eps and eps > 0 else None
    pb = round(r["now"] / bv, 1) if bv and bv > 0 else None
    about = trim(p.get("summary")) or trim(desc.get(str(raw[r["symbol"]]["id"])))
    facts = []
    if p.get("revenue") is not None: facts.append(["Revenue (TTM)", inr(p["revenue"])])
    if p.get("ebitda") is not None: facts.append(["EBITDA (TTM)", inr(p["ebitda"])])
    if p.get("employees"): facts.append(["Employees", f"{p['employees']:,}"])
    mb.append(dict(n=re.sub(r" (Ltd\.|Limited)$", "", r["company"]), s=r["symbol"], ind=r["industry"], d=r["listed"], b=r["band"],
        i=r["issue"], o=r["listing_open"], lg=r["listing_gain"], c=r["now"], x=r["multiple"], g=r["total_gain"], y=r["cagr"] if r["cagr"] == "" else r["cagr"],
        yrs=r["years"], t=r["tag"], about=about, facts=facts, read=perf_read(r) + fin_read(p, r["now"], mc), web=p.get("website"),
        pe=pe, pb=pb, vt=vtag(pe, eps is not None and eps <= 0), ps=r["price_src"], mc=round(mc / 1e7) if mc else None, mcb=sh["basis"] if sh else None, why=note["why"], outlook=note["outlook"], links=note["src"], conf=note.get("conf", "medium"), src="Yahoo Finance" if p.get("summary") else "Chittorgarh"))

SNOTES = {}
for f in sorted(glob.glob("data/research_sme/notes_*.json")): SNOTES.update(json.load(open(f)))
def snote(r):
    for k, n in SNOTES.items():
        if r["company"].startswith(n.get("match", k)) or k == r["symbol"]: return n

sme = []
from datetime import date
for r in csv.DictReader(open("data/sme_tech_last5y.csv")):
    iss, op, cur = fl(r["issue_price"]), fl(r["listing_open"]), fl(r["current_price"])
    g = fl(r["adj_gain_pct"]); x = (1 + g / 100) if g is not None else None
    yrs = (date(2026,10,15) - date.fromisoformat(r["listing_date"])).days / 365.25
    cagr = round((x ** (1 / yrs) - 1) * 100, 1) if x and x > 0 and yrs >= 1 else ""
    n = snote(r)
    mc = mcb = pe = None
    if n.get("mcref") and cur:
        mc = n["mcref"][0] * cur / n["mcref"][1]
        mcb = f"reported market cap of ₹{n['mcref'][0]:,.0f} crore at ₹{n['mcref'][1]:,.2f}, scaled to the current price"
    elif n.get("mc_direct"):
        mc = n["mc_direct"][0]; mcb = f"reported market cap of ₹{mc:,.0f} crore as of {n['mc_direct'][1]} (not scaled to today's price)"
    if n.get("pe"):
        pe = round(n["pe"] * cur / n["mcref"][1], 1) if n.get("mcref") and cur else n["pe"]
    loss = n["why"].lower().count("loss-making") > 0 or "negative" in n["why"].lower() and "p/e" in n["why"].lower()
    sme.append(dict(n=re.sub(r" (Ltd\.|Limited)$", "", r["company"]), s=r["symbol"], d=r["listing_date"], b=r["price_band"], i=iss, o=op,
        lg=round((op/iss-1)*100,1) if op and iss else None, c=cur, x=round(x,2) if x else None, g=g, y=cagr, yrs=round(yrs,2),
        ps=r["price_src"], about=r["description"], adj=r["has_split_data"] == "True",
        mc=round(mc) if mc is not None and mc >= 10 else (round(mc, 1) if mc is not None else None), mcb=mcb, pe=pe, vt=vtag(pe, loss and pe is None),
        why=n["why"], outlook=n["outlook"], links=n["src"], conf=n.get("conf", "low")))

tpl = open("scripts/page_template.html").read()
allr = json.load(open("data/all_ipos.json"))
for r in allr: r["ss"] = "approximate, from industry and business description"
open(OUT, "w").write(tpl.replace("__MB__", json.dumps(mb, ensure_ascii=False)).replace("__SME__", json.dumps(sme, ensure_ascii=False)).replace("__ALL__", json.dumps(allr, ensure_ascii=False)))
print(len(mb), len(sme))
