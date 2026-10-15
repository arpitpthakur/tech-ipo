import csv, json, re
desc = json.load(open('data/descriptions.json'))
raw = {r['company']: r for r in json.load(open('data/ipos_raw.json'))['rows'] if r['board'] == 'sme'}
KW = re.compile(r"\b(software|saas|it services|it solutions|it consult\w*|information technology|web ?(site|development|hosting)|mobile app\w*|app development|application development|cloud|cyber ?security|data analytics|artificial intelligence|machine learning|\bAI\b|blockchain|digital (marketing|platform|solutions|services|payment\w*)|e-?commerce|online (platform|marketplace|portal)|fintech|payment (gateway|solutions)|erp|iot|internet of things|augmented reality|virtual reality|data cent(er|re)|web ?portal|technology (platform|solutions|services)|software development|system integrat\w*|edtech|telematics|gps tracking|bpo|business process outsourc\w*|call cent(er|re))\b", re.I)
rows = list(csv.DictReader(open('data/sme.csv')))
out = []
for r in rows:
    d = desc.get(str(raw[r['company']]['id'])) if r['company'] in raw else None
    hit = sorted({m.group(0).lower() for m in KW.finditer(d or '')})
    r['description'] = d or ''
    r['tech_keywords'] = ';'.join(hit)
    r['is_tech'] = bool(hit)
    out.append(r)
w = csv.DictWriter(open('data/sme_classified.csv', 'w'), fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)
t = [r for r in out if r['is_tech']]
print(len(t), 'of', len(out))
for r in sorted(t, key=lambda r: r['listing_date']):
    print(f"{r['listing_date']} | {r['company'][:34]:34} | {r['tech_keywords'][:40]:40} | {r['description'][:110]}")
