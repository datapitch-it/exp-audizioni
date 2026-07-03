"""
Aggrega data/soggetti_auditi.json (livello "menzione", una riga per soggetto
per audizione) in data/soggetti_index.json a livello "soggetto": un record
per ogni nome distinto, con tutte le sue audizioni annidate.

Dedup solo su stringa esatta del nome (nessun fuzzy-matching di varianti
grafiche): e' lo stesso limite gia' documentato per l'estrazione dei soggetti.
"""
import json
import collections
import re
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_categories import classify_category

ROOT = Path(__file__).resolve().parent.parent
SOGGETTI_PATH = ROOT / "data" / "soggetti_auditi.json"
OUT_PATH = ROOT / "data" / "soggetti_index.json"


def slugify(name):
    s = name.lower().strip()
    s = re.sub(r"[àá]", "a", s)
    s = re.sub(r"[èé]", "e", s)
    s = re.sub(r"[ìí]", "i", s)
    s = re.sub(r"[òó]", "o", s)
    s = re.sub(r"[ùú]", "u", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    return s.strip("-")


def build_group(records, subject_type):
    by_name = collections.defaultdict(list)
    for r in records:
        by_name[r["subject_name"]].append(r)

    out = []
    for name, rows in by_name.items():
        committees = collections.Counter(r["committee"] for r in rows)
        audizioni = sorted(
            (
                {
                    "date": r["date"],
                    "committee": r["committee"],
                    "title": r["audizione_title"],
                    "bulletin_url": r.get("bulletin_url"),
                    "discussion_uri": r.get("discussion_uri"),
                }
                for r in rows
            ),
            key=lambda a: a["date"] or "",
        )
        dates = [a["date"] for a in audizioni if a["date"]]
        entry = {
            "slug": slugify(name),
            "name": name,
            "type": subject_type,
            "count": len(rows),
            "committees": committees.most_common(),
            "date_min": min(dates) if dates else None,
            "date_max": max(dates) if dates else None,
            "audizioni": audizioni,
        }
        if subject_type == "organization":
            entry["category"] = classify_category(name)
        out.append(entry)

    out.sort(key=lambda e: -e["count"])
    return out


def main():
    with open(SOGGETTI_PATH, encoding="utf-8") as f:
        records = json.load(f)

    persons = [r for r in records if r["subject_type"] == "person" and r["subject_name"]]
    orgs = [r for r in records if r["subject_type"] == "organization" and r["subject_name"]]

    data = {
        "persone": build_group(persons, "person"),
        "organizzazioni": build_group(orgs, "organization"),
    }

    # disambigua eventuali slug duplicati (nomi diversi che si normalizzano uguali)
    for group in (data["persone"], data["organizzazioni"]):
        seen = collections.Counter()
        for e in group:
            seen[e["slug"]] += 1
            if seen[e["slug"]] > 1:
                e["slug"] = f"{e['slug']}-{seen[e['slug']]}"

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Persone: {len(data['persone'])} | Organizzazioni: {len(data['organizzazioni'])}")
    print(f"Scritto in {OUT_PATH}")


if __name__ == "__main__":
    main()
