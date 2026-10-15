import json, re, html, subprocess
from concurrent.futures import ThreadPoolExecutor

raw = json.load(open("data/ipos_raw.json"))["rows"]

def desc(r):
    url = f"https://www.chittorgarh.com/ipo/{r['slug']}/{r['id']}/"
    for _ in range(3):
        out = subprocess.run(["curl", "-s", "-m", "30", "-A", "Mozilla/5.0", url], capture_output=True, text=True).stdout
        t = re.sub(r"\s+", " ", html.unescape(re.sub(r"<(script|style)[^>]*>.*?</\1>|<[^>]+>", " ", out, flags=re.S)))
        m = re.search(r"About .{3,80}? Updated on \w+ \d+, \d{4} (.{40,700})", t)
        if m:
            return r["id"], m.group(1)
    return r["id"], None

with ThreadPoolExecutor(24) as ex:
    res = dict(ex.map(desc, raw))
json.dump(res, open("data/descriptions.json", "w"))
print(len(res), sum(v is None for v in res.values()), "missing")
