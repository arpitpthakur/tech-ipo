import csv, statistics as st, collections
tags = {r['symbol']: r['startup_tag'] for r in csv.DictReader(open('data/startup_tags.csv'))}
rows = list(csv.DictReader(open('data/tech_last5y_validated.csv')))
for r in rows:
    r['tag'] = tags[r['symbol']]
    r['gain'] = float(r['adj_gain_pct'])
    r['pop'] = (float(r['listing_open']) / float(r['issue_price']) - 1) * 100
    r['year'] = r['listing_date'][:4]
    r['after_pop'] = ((1 + r['gain'] / 100) / (1 + r['pop'] / 100) - 1) * 100

def summ(name, g):
    if not g: return
    gains = [r['gain'] for r in g]; pops = [r['pop'] for r in g]
    print(f"| {name} | {len(g)} | {sum(x>0 for x in gains)/len(g)*100:.0f}% | {st.median(pops):+.0f}% | {st.median(gains):+.0f}% | {st.mean(gains):+.0f}% | {min(gains):+.0f}% | {max(gains):+.0f}% |")

hdr = "| Group | N | % above issue | Median listing pop | Median gain | Mean gain | Worst | Best |\n|---|---|---|---|---|---|---|---|"
def table(title, key):
    print(f"\n**{title}**\n{hdr}")
    gs = collections.defaultdict(list)
    for r in rows: gs[key(r)].append(r)
    for k in sorted(gs): summ(k, gs[k])

summ_all = rows
print(hdr); summ('All 61', rows)
table('By startup tag', lambda r: r['tag'])
table('By listing year', lambda r: r['year'])
table('By industry', lambda r: r['industry'])
print("\nPop vs now (listing-open buyer):")
op = [r for r in rows if r['pop'] > 0]
print(f"listed above issue: {len(op)}/61; of those, now below listing open: {sum(r['after_pop']<0 for r in op)}")
print("pop>=30%:", sum(r['pop']>=30 for r in rows), "-> still above issue:", sum(r['pop']>=30 and r['gain']>0 for r in rows))
print("\nStartups detail (sorted by gain):")
for r in sorted([r for r in rows if r['tag']=='Startup'], key=lambda r:-r['gain']):
    print(f"| {r['company'][:26]} | {r['listing_date'][:7]} | {r['pop']:+.0f}% | {r['gain']:+.0f}% | {r['after_pop']:+.0f}% |")
