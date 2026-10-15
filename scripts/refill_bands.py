"""Re-run only the price-band step on data/ipos_raw.json (rows already collected)."""
import json
from concurrent.futures import ThreadPoolExecutor

from fetch_ipos import OUT, band

path = OUT / "ipos_raw.json"
d = json.loads(path.read_text())
with ThreadPoolExecutor(8) as ex:
    d["rows"] = list(ex.map(band, d["rows"]))
path.write_text(json.dumps(d, indent=1))
print("bands found:", sum(1 for r in d["rows"] if r["band_low"]), "of", len(d["rows"]))
