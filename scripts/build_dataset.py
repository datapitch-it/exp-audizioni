"""
Aggrega audizioni.json + data/bills_cache.json in un unico dataset
(data/report_data.json) pronto per essere consumato dal report HTML.

Per ogni audizione calcola:
  - categoria del soggetto audito (euristica, vedi lib_categories.py)
  - entita' note citate nel titolo (per le classifiche "soggetto piu' audito")
  - se collegata a un provvedimento: tipologia atto e fase dell'iter

Poi produce:
  - sintesi generale (totali)
  - una scheda per ciascuna Commissione (numero audizioni, atti, iter, categorie, top soggetto)
  - classifiche trasversali (commissioni piu' attive, soggetti piu' auditi, categorie piu' audite)
  - serie temporale mensile (utile per un grafico di andamento, assente nel PDF originale
    ma coerente con l'obiettivo di "analizzare i dati della XIX legislatura")
"""
import json
import collections
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_categories import classify_category, find_known_entities, CATEGORIES

ROOT = Path(__file__).resolve().parent.parent
AUDIZIONI_PATH = ROOT / "audizioni.json"
BILLS_CACHE_PATH = ROOT / "data" / "bills_cache.json"
OUT_PATH = ROOT / "data" / "report_data.json"


def load():
    with open(AUDIZIONI_PATH, encoding="utf-8") as f:
        audizioni = json.load(f)
    with open(BILLS_CACHE_PATH, encoding="utf-8") as f:
        bills = json.load(f)
    return audizioni, bills


def first_bill_uri(raw):
    for uri in (raw or "").split(","):
        uri = uri.strip()
        if uri:
            return uri
    return None


def main():
    audizioni, bills = load()

    for rec in audizioni:
        rec["_category"] = classify_category(rec["title"])
        rec["_entities"] = find_known_entities(rec["title"])
        uri = first_bill_uri(rec.get("bill_uris", ""))
        bill = bills.get(uri) if uri else None
        rec["_tipologia_atto"] = bill["tipologia"] if bill else None
        rec["_fase_iter"] = bill["fase_iter"] if bill else None
        rec["_month"] = rec["date"][:7] if rec.get("date") else None

    total = len(audizioni)
    with_bill = sum(1 for r in audizioni if r["_tipologia_atto"])

    # ---- sintesi generale ----
    committees = sorted(set(r["committee"] for r in audizioni))
    cat_counts_global = collections.Counter(r["_category"] for r in audizioni)
    entity_counts_global = collections.Counter()
    for r in audizioni:
        entity_counts_global.update(r["_entities"])
    tipologia_counts_global = collections.Counter(r["_tipologia_atto"] for r in audizioni if r["_tipologia_atto"])
    fase_counts_global = collections.Counter(r["_fase_iter"] for r in audizioni if r["_fase_iter"])

    month_counts = collections.Counter(r["_month"] for r in audizioni if r["_month"])

    # ---- per commissione ----
    per_committee = {}
    for c in committees:
        rows = [r for r in audizioni if r["committee"] == c]
        cat_counts = collections.Counter(r["_category"] for r in rows)
        entity_counts = collections.Counter()
        for r in rows:
            entity_counts.update(r["_entities"])
        tipologia_counts = collections.Counter(r["_tipologia_atto"] for r in rows if r["_tipologia_atto"])
        fase_counts = collections.Counter(r["_fase_iter"] for r in rows if r["_fase_iter"])
        n_bills = len(set(first_bill_uri(r.get("bill_uris", "")) for r in rows if first_bill_uri(r.get("bill_uris", ""))))
        top_entity = entity_counts.most_common(1)
        per_committee[c] = {
            "totale_audizioni": len(rows),
            "n_atti_distinti": n_bills,
            "categorie": {cat: cat_counts.get(cat, 0) for cat in CATEGORIES},
            "tipologia_atti": dict(tipologia_counts),
            "fase_iter": dict(fase_counts),
            "top_soggetti": entity_counts.most_common(5),
            "soggetto_piu_audito": {"nome": top_entity[0][0], "volte": top_entity[0][1]} if top_entity else None,
        }

    # ---- classifiche trasversali ----
    ranking_committees = sorted(
        ((c, d["totale_audizioni"]) for c, d in per_committee.items()),
        key=lambda x: -x[1],
    )

    data = {
        "meta": {
            "legislatura": 19,
            "camera_only": True,
            "nota_senato": "Il Senato non e' coperto: l'endpoint SPARQL del Senato non espone data/commissione delle audizioni informali.",
            "totale_audizioni": total,
            "totale_commissioni": len(committees),
            "audizioni_con_atto_collegato": with_bill,
            "atti_distinti_arricchiti": len(bills),
            "metodo_classificazione": "euristico a regole/dizionario (nessun registro ufficiale collegato); vedi scripts/lib_categories.py",
        },
        "sintesi_generale": {
            "categorie": {cat: cat_counts_global.get(cat, 0) for cat in CATEGORIES},
            "top_soggetti": entity_counts_global.most_common(15),
            "tipologia_atti": dict(tipologia_counts_global),
            "fase_iter": dict(fase_counts_global),
            "andamento_mensile": sorted(month_counts.items()),
        },
        "ranking_commissioni": ranking_committees,
        "per_commissione": per_committee,
    }

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Scritto {OUT_PATH}")
    print(f"Totale audizioni: {total} | con atto collegato: {with_bill} | commissioni: {len(committees)}")


if __name__ == "__main__":
    main()
