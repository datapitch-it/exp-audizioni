"""
Arricchisce i bill_uris unici presenti in audizioni.json con:
  - tipo atto (da `italianparliament bill show`)
  - fase iter corrente, ricavata dall'ultimo stato di `italianparliament bill-progress list --uri ...`

Usa una cache locale su file (data/bills_cache.json) per evitare di rifare le
stesse chiamate ad ogni esecuzione (rate limit dell'endpoint SPARQL).
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
AUDIZIONI_PATH = ROOT / "audizioni.json"
CACHE_PATH = ROOT / "data" / "bills_cache.json"


def run_cli(args):
    result = subprocess.run(
        ["italianparliament", *args, "--format", "jsonl"],
        capture_output=True, text=True, timeout=60,
    )
    if result.returncode != 0:
        return []
    rows = []
    for line in result.stdout.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError:
            pass
    return rows


def classify_tipologia(title, initiative):
    t = (title or "").lower()
    if "decreto-legge" in t or "decreto legge" in t:
        return "Decreto-legge/Legge di conversione"
    if "legge costituzionale" in t:
        return "Legge Costituzionale"
    if (initiative or "").lower() == "popolare":
        return "Legge di iniziativa popolare"
    return "Proposta di legge/Disegno di legge"


ITER_BUCKETS = [
    ("Pubblicato in Gazzetta Ufficiale", ["pubblicat", "gazzetta"]),
    ("Approvato", ["approvat"]),
    ("Ritirato/Decaduto", ["ritirat", "decadut"]),
]


def classify_iter_phase(description, statuses):
    desc = (description or "").lower()
    if "gazzetta ufficiale" in desc or "pubblicata" in desc:
        return "Pubblicato in Gazzetta Ufficiale"
    if not statuses:
        return "In esame"
    last = max(statuses, key=lambda s: s.get("status_date") or "")
    text = (last.get("status") or "").lower()
    for bucket, keywords in ITER_BUCKETS:
        if any(k in text for k in keywords):
            return bucket
    return "In esame"


def main():
    with open(AUDIZIONI_PATH, encoding="utf-8") as f:
        audizioni = json.load(f)

    unique_uris = set()
    for rec in audizioni:
        raw = rec.get("bill_uris", "")
        for uri in raw.split(","):
            uri = uri.strip()
            if uri:
                unique_uris.add(uri)

    print(f"bill_uris unici da arricchire: {len(unique_uris)}", file=sys.stderr)

    cache = {}
    if CACHE_PATH.exists():
        with open(CACHE_PATH, encoding="utf-8") as f:
            cache = json.load(f)

    todo = [u for u in unique_uris if u not in cache]
    print(f"gia' in cache: {len(unique_uris) - len(todo)}, da scaricare: {len(todo)}", file=sys.stderr)

    for i, uri in enumerate(todo, 1):
        show_rows = run_cli(["bill", "show", "--uri", uri])
        progress_rows = run_cli(["bill-progress", "list", "--uri", uri])
        row = show_rows[0] if show_rows else {}
        title = row.get("title", "")
        tipologia = classify_tipologia(title, row.get("initiative"))
        fase_iter = classify_iter_phase(row.get("description"), progress_rows)
        cache[uri] = {
            "title": title.strip(),
            "tipologia": tipologia,
            "fase_iter": fase_iter,
            "initiative": row.get("initiative"),
            "n_status": len(progress_rows),
        }
        if i % 10 == 0 or i == len(todo):
            print(f"  {i}/{len(todo)}", file=sys.stderr)
            with open(CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)

    with open(CACHE_PATH, "w", encoding="utf-8") as f:
        json.dump(cache, f, ensure_ascii=False, indent=2)
    print(f"Cache scritta in {CACHE_PATH} ({len(cache)} bill totali)", file=sys.stderr)


if __name__ == "__main__":
    main()
