"""
Estrae i singoli soggetti auditi (persone o organizzazioni) dal campo libero
"title" di ogni audizione in audizioni.json.

Non e' un NER: e' un estrattore a regole pensato sui pattern ricorrenti del
bollettino della Camera. Ogni riga estratta mantiene sempre il testo grezzo
originale (subject_raw) cosi' che eventuali errori dell'euristica siano
sempre verificabili/correggibili a valle.

Output: data/soggetti_auditi.json — un record per ogni soggetto individuato
(un'audizione con piu' auditi produce piu' record, tutti con lo stesso
audizione_index/bulletin_url per poterli ricollegare).
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from lib_categories import find_known_entities

ROOT = Path(__file__).resolve().parent.parent
AUDIZIONI_PATH = ROOT / "audizioni.json"
OUT_PATH = ROOT / "data" / "soggetti_auditi.json"

# ---- pulizia -----------------------------------------------------------

FILLER_PATTERNS = [
    r"Svolgimento,?\s+ai sensi dell'articolo\s+\d+[,.]?\s*(?:comma\s+\d+,?)?\s*del [Rr]egolamento,?\s*e conclusione\s*-\s*",
    r"Svolgimento e conclusione\s*-\s*",
    r"Seguito dell['’]\s*",
    r"Esame testimoniale e successiva libera\s*",
    r",?\s*in videoconferenza,?",
    r",?\s*in videocoferenza,?",  # refuso presente nei dati originali
    r"\binformale\b,?",
]

CONTEXT_CUT_MARKERS = [
    r"\bnell['’]ambito\b",
    r"\bcon riferimento al filone\b",
    r"\bin relazione a\b",
    r"\bsulle linee programmatiche\b",
    r"\bai fini dell['’]inchiesta\b",
    r"\bai sensi dell['’]articolo\s+\d+\b",
]
CONTEXT_CUT_RE = re.compile("|".join(CONTEXT_CUT_MARKERS), re.IGNORECASE)

LEADING_CONNECTOR_RE = re.compile(r"^(?:di|del|della|dei|degli|dell['’])\s+", re.IGNORECASE)

ROLE_STOPWORDS = {
    "Direttore", "Direttrice", "Direttivo", "Presidente", "Vicepresidente", "Segretario",
    "Segretaria", "Sottosegretario", "Sottosegretaria", "Ministro", "Ministra", "Assessore",
    "Procuratore", "Procuratrice", "Capo", "Comandante", "Generale", "Professore",
    "Professoressa", "Dottore", "Dottoressa", "Avvocato", "Prefetto", "Monsignor",
    "Ammiraglio", "Ispettore", "Consigliere", "Consigliera", "Rappresentante",
    "Rappresentanti", "Coordinatore", "Coordinatrice", "Responsabile", "Portavoce",
    "Amministratore", "Amministratrice", "Viceprocuratore", "Agenzia", "Ministero",
    "Autorità", "Regione", "Provincia", "Comune", "Dipartimento", "Procura", "Tribunale",
    "Consiglio", "Corte", "Banca", "Fondazione", "Associazione", "Confederazione",
    "Unione", "Istituto", "Comando", "Guardia", "Polizia", "Camera", "Commissione",
    "Ordine", "Università", "Audizione", "Indagine", "Svolgimento", "Seguito",
    "Vice", "Già", "Presidenza", "Gruppo", "Federazione", "Sindacato", "Comitato",
    "Istituto", "Comitato Tecnico",
}

HONORIFIC_PREFIX_RE = re.compile(
    r"^(?:(?:di|del|della|dei|degli|dell['’])\s+)?"
    r"(?:(?:professor(?:essa)?|dottor(?:essa)?|avvocato|già|gia['’]|"
    r"dott\.|prof\.|sen\.|on\.|gen\.|amm\.|ing\.|avv\.)\s+)*",
    re.IGNORECASE,
)

NAME_CANDIDATE_RE = re.compile(
    r"(?:[A-ZÀ-Ý][a-zà-ÿ'’.]+(?:\s+|-)){1,3}[A-ZÀ-Ý][a-zà-ÿ'’.]+"
)


def clean_segment(text):
    for pat in FILLER_PATTERNS:
        text = re.sub(pat, " ", text, flags=re.IGNORECASE)
    text = re.sub(r"^\s*Audizione\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text).strip(" .,-")
    m = CONTEXT_CUT_RE.search(text)
    if m and m.start() > 0:
        text = text[: m.start()].strip(" .,-")
    return text


def split_title_into_segments(title):
    """Gestisce titoli con piu' occorrenze della parola 'Audizione'."""
    idxs = [m.start() for m in re.finditer(r"\bAudizione\b", title, flags=re.IGNORECASE)]
    if not idxs:
        return [title]
    idxs.append(len(title))
    return [title[idxs[i]:idxs[i + 1]] for i in range(len(idxs) - 1)]


# ---- estrazione organizzazioni ------------------------------------------

ORG_INTRO_RE = re.compile(
    r"^rappresentant[ei]\s+(?:di|del|della|dei|degli|dell['’])\s+", re.IGNORECASE
)


def split_org_list(remainder):
    # preferisci lo split su "di/del/..." ripetuto (es. "di X, di Y, e di Z")
    parts = re.split(r",\s*(?:e\s+)?(?:di|del|della|dei|degli|dell[\'’])\s+", remainder, flags=re.IGNORECASE)
    if len(parts) > 1:
        return parts
    # altrimenti lista semplice "X, Y e Z"
    return re.split(r",\s*|\s+e\s+", remainder)


def extract_organizations(segment):
    remainder = ORG_INTRO_RE.sub("", segment)
    parts = [p.strip(" .,") for p in split_org_list(remainder) if p.strip(" .,")]
    if not parts:
        parts = [remainder.strip(" .,")]
    results = []
    for p in parts:
        if not p:
            continue
        known = find_known_entities(p)
        name = known[0] if known else p
        results.append({"subject_type": "organization", "subject_name": name, "subject_raw": p})
    return results


# ---- estrazione persone --------------------------------------------------

PERSON_SPLIT_RE = re.compile(
    r",?\s+e\s+(?=(?:del|della|dei|degli|dell[\'’]|di)\s)", re.IGNORECASE
)

PLAIN_NAME_LIST_RE = re.compile(
    r"^(?:[A-ZÀ-Ý][\wà-ÿ'’]+(?:\s+[A-ZÀ-Ý][\wà-ÿ'’]+)+)"
    r"(?:,\s*[A-ZÀ-Ý][\wà-ÿ'’]+(?:\s+[A-ZÀ-Ý][\wà-ÿ'’]+)+)*"
    r"(?:,?\s+e\s+[A-ZÀ-Ý][\wà-ÿ'’]+(?:\s+[A-ZÀ-Ý][\wà-ÿ'’]+)+)?$"
)


def guess_person_name(chunk):
    """
    Preferisce il candidato che compare in posizione 0 (pattern "Nome Cognome,
    ruolo..."); se il primo candidato valido non e' in testa (pattern "ruolo,
    Nome Cognome"), preferisce l'ULTIMO candidato del testo, perche' nella
    convenzione dei titoli Camera quando il ruolo precede il nome, il nome
    compare alla fine, dopo l'ultima virgola.
    """
    chunk = HONORIFIC_PREFIX_RE.sub("", chunk, count=1)
    matches = list(NAME_CANDIDATE_RE.finditer(chunk))
    filtered = [m for m in matches if m.group().split()[0] not in ROLE_STOPWORDS]
    if not filtered:
        return None
    lead_offset = len(chunk) - len(chunk.lstrip())
    first = filtered[0]
    if first.start() <= lead_offset:
        return first.group().strip()
    return filtered[-1].group().strip()


def extract_persons(segment):
    core = LEADING_CONNECTOR_RE.sub("", segment)
    if PLAIN_NAME_LIST_RE.match(core):
        names = re.split(r",\s*|\s+e\s+", core)
        return [
            {"subject_type": "person", "subject_name": n.strip(), "subject_raw": n.strip()}
            for n in names if n.strip()
        ]

    chunks = [c.strip(" .,") for c in PERSON_SPLIT_RE.split(segment) if c.strip(" .,")]
    # scarta lo split se produce frammenti senza virgola: e' segno che il
    # separatore "e del/della/..." apparteneva al nome di un ente composto
    # (es. "Agenzia delle Dogane e dei Monopoli") e non separava due persone
    if len(chunks) > 1 and any("," not in c for c in chunks):
        chunks = [segment.strip(" .,")]
    if not chunks:
        chunks = [segment.strip(" .,")]

    results = []
    for chunk in chunks:
        name = guess_person_name(chunk)
        if name is None:
            known = find_known_entities(chunk)
            if known:
                results.append({"subject_type": "organization", "subject_name": known[0], "subject_raw": chunk})
                continue
        results.append({"subject_type": "person", "subject_name": name, "subject_raw": chunk})
    return results


# ---- pipeline principale --------------------------------------------------

def extract_subjects_from_title(title):
    out = []
    for raw_segment in split_title_into_segments(title):
        segment = clean_segment(raw_segment)
        if not segment:
            continue
        core = LEADING_CONNECTOR_RE.sub("", segment)
        if ORG_INTRO_RE.match(core):
            out.extend(extract_organizations(core))
        else:
            out.extend(extract_persons(segment))
    return out


def main():
    with open(AUDIZIONI_PATH, encoding="utf-8") as f:
        audizioni = json.load(f)

    records = []
    for idx, rec in enumerate(audizioni):
        subjects = extract_subjects_from_title(rec["title"])
        for s in subjects:
            records.append({
                "audizione_index": idx,
                "date": rec["date"],
                "committee": rec["committee"],
                "chamber": rec["chamber"],
                "legislature": rec["legislature"],
                **s,
                "audizione_title": rec["title"],
                "bulletin_url": rec.get("bulletin_url"),
                "discussion_uri": rec.get("discussion_uri"),
            })

    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)

    n_person = sum(1 for r in records if r["subject_type"] == "person")
    n_org = sum(1 for r in records if r["subject_type"] == "organization")
    n_person_unresolved = sum(1 for r in records if r["subject_type"] == "person" and not r["subject_name"])
    print(f"Audizioni processate: {len(audizioni)}")
    print(f"Soggetti estratti: {len(records)} (persone: {n_person}, organizzazioni: {n_org})")
    print(f"Persone senza nome risolto (fallback su subject_raw): {n_person_unresolved}")
    print(f"Scritto in {OUT_PATH}")


if __name__ == "__main__":
    main()
