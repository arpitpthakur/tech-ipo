import csv, json, statistics as st
S = 'data/splits_cache.json'
sp = json.load(open(S))
_K = json.load(open('data/kite_ltp.json'))
KITE = {**_K['sme_bse'], **_K['sme']}
BYCO = _K['sme_bse_by_company']
OVR = _K['sme_price_override']
EXCLUDE = ('Sellowrap',)
KEEP = {1,2,3,5,6,7,8,9,13,14,15,16,17,18,21,22,23,26,28,29,30,31,33,34,35,37,39,41,42,43,45,47,48,50,53,54,61,62,63,64,65,66,68,70,71,74,75,76,77,79,81,85,89,92,96,98,99,102,103,104,105,106,107,108,109,110,112,115,116,122,124,125,134,136,137,139,144,145,147,150,155,157,158}
cand = [r for r in csv.DictReader(open('data/sme_classified.csv')) if r['is_tech'] == 'True']
out = []
for i, r in enumerate(cand):
    if i not in KEEP or r['company'].startswith(EXCLUDE): continue
    fac = 1
    for d, ratio in ([] if r['symbol'] in OVR else sp.get('sme:' + r['symbol'], []) or []):
        if d > r['listing_date']: fac *= ratio
    co = next((v for n, v in BYCO.items() if r['company'].startswith(n)), None)
    px = KITE.get(r['symbol']) if r['symbol'] else co
    r['price_src'] = 'kite' if px is not None else 'chittorgarh'
    if r['symbol'] in OVR:
        px, r['price_src'] = OVR[r['symbol']], 'web'
    if px is not None: r['current_price'] = str(px)
    r['has_split_data'] = ('sme:' + r['symbol']) in sp and sp['sme:' + r['symbol']] is not None
    r['split_factor'] = fac
    if r['current_price']:
        r['adj_gain_pct'] = round((float(r['current_price']) * fac / float(r['issue_price']) - 1) * 100, 1)
    else:
        r['adj_gain_pct'] = ''
    out.append(r)
keys = ['company','symbol','listing_date','price_band','issue_price','listing_open','current_price','split_factor','has_split_data','adj_gain_pct','price_src','tech_keywords','description']
w = csv.DictWriter(open('data/sme_tech_last5y.csv', 'w'), fieldnames=keys, extrasaction='ignore'); w.writeheader(); w.writerows(sorted(out, key=lambda r: r['listing_date']))
g = [float(r['adj_gain_pct']) for r in out if r['adj_gain_pct'] != '']
pop = [(float(r['listing_open'])/float(r['issue_price'])-1)*100 for r in out if r['listing_open']]
print(len(out), 'SME tech; with price', len(g), '; split data', sum(r['has_split_data'] for r in out), '; split-adjusted', sum(r['split_factor']!=1 for r in out))
print(f"above issue {sum(x>0 for x in g)/len(g)*100:.0f}% | median pop {st.median(pop):+.0f}% | median gain {st.median(g):+.0f}% | mean {st.mean(g):+.0f}% | worst {min(g):+.0f}% | best {max(g):+.0f}%")
yr = {}
for r in out:
    if r['adj_gain_pct'] != '': yr.setdefault(r['listing_date'][:4], []).append(float(r['adj_gain_pct']))
for y in sorted(yr): print(y, len(yr[y]), f"{sum(x>0 for x in yr[y])/len(yr[y])*100:.0f}% up, median {st.median(yr[y]):+.0f}%")
print('\nTop 5 / bottom 5')
s = sorted([r for r in out if r['adj_gain_pct']!=''], key=lambda r: float(r['adj_gain_pct']))
for r in s[:5] + s[-5:]: print(r['company'][:30], r['listing_date'], r['issue_price'], r['current_price'], r['adj_gain_pct'], r['has_split_data'])
