"""
Regole euristiche (dizionario curato + keyword matching) per classificare
il testo libero delle audizioni (campo "title") in:
  - una categoria del soggetto audito
  - eventuali soggetti "noti" (dizionario di entita' ricorrenti) menzionati nel titolo

Limiti dichiarati: non e' un NER, e' un classificatore a regole. Il campo
"title" della Camera e' testo libero, spesso con piu' soggetti nella stessa
audizione: qui si assegna UNA categoria "prevalente" per audizione (prima
regola che matcha, in ordine di priorita') e si estraggono TUTTE le entita'
note citate per le classifiche "soggetto piu' audito".
"""
import re

CATEGORIES = [
    "Sindacati e associazioni di categoria",
    "Autorità indipendenti/soggetti istituzionali",
    "Aziende partecipate",
    "Aziende",
    "Associazioni e organizzazioni della società civile",
    "Esperti/Professori/Professionisti",
    "Altro",
]

# Dizionario di entita' note: nome canonico -> lista di pattern regex (case-insensitive)
# usato sia per il conteggio "soggetto piu' audito" sia (raggruppato sotto) per le regole di categoria.
ENTITIES_SINDACATI_CATEGORIA = {
    "CGIL": [r"\bCGIL\b"],
    "CISL": [r"\bCISL\b"],
    "UIL": [r"\bUIL\b"],
    "UGL": [r"\bUGL\b"],
    "Confindustria": [r"\bConfindustria\b"],
    "Confcommercio": [r"\bConfcommercio\b"],
    "Confesercenti": [r"\bConfesercenti\b"],
    "Confartigianato": [r"\bConfartigianato\b"],
    "CNA": [r"\bCNA\b"],
    "Coldiretti": [r"\bColdiretti\b"],
    "Confagricoltura": [r"\bConfagricoltura\b"],
    "CIA - Confederazione Italiana Agricoltori": [r"\bCIA\b.{0,40}Agricoltori", r"Confederazione Italiana Agricoltori"],
    "Copagri": [r"\bCopagri\b"],
    "ANCI": [r"\bANCI\b"],
    "UPI": [r"\bUPI\b"],
    "Confapi": [r"\bConfapi\b"],
    "Confcooperative": [r"\bConfcooperative\b"],
    "Legacoop": [r"\bLegacoop\b"],
    "ANIA": [r"\bANIA\b"],
    "ABI": [r"\bABI\b"],
    "ANCE": [r"\bANCE\b"],
    "Federfarma": [r"\bFederfarma\b"],
    "Confedilizia": [r"\bConfedilizia\b"],
    "Assonime": [r"\bAssonime\b"],
    "Confimi Industria": [r"\bConfimi\s*Industria\b"],
}

ENTITIES_ISTITUZIONALI = {
    "ISPRA": [r"\bISPRA\b"],
    "ISTAT": [r"\bISTAT\b"],
    "ANAC": [r"\bANAC\b"],
    "Banca d'Italia": [r"Banca d[’']Italia"],
    "Corte dei Conti": [r"Corte dei [Cc]onti"],
    "AGCM": [r"\bAGCM\b"],
    "AGCOM": [r"\bAGCOM\b"],
    "Garante Privacy": [r"Garante per la protezione dei dati personali"],
    "INPS": [r"\bINPS\b"],
    "INAIL": [r"\bINAIL\b"],
    "CNR": [r"\bCNR\b"],
    "INGV": [r"\bINGV\b"],
}

ENTITIES_AZIENDE_PARTECIPATE = {
    "ENEL": [r"\bENEL\b"],
    "ENI": [r"\bENI\b"],
    "Ferrovie dello Stato": [r"Ferrovie dello Stato", r"\bRFI\b", r"Trenitalia"],
    "Poste Italiane": [r"Poste Italiane"],
    "RAI": [r"\bRAI\b"],
    "Leonardo": [r"\bLeonardo\s+S\.?p\.?A\.?\b"],
    "Cassa Depositi e Prestiti": [r"Cassa Depositi e Prestiti", r"\bCDP\b"],
    "Terna": [r"\bTerna\b"],
    "Snam": [r"\bSnam\b"],
}

KNOWN_ENTITIES = {**ENTITIES_SINDACATI_CATEGORIA, **ENTITIES_ISTITUZIONALI, **ENTITIES_AZIENDE_PARTECIPATE}

# Regole di categoria, in ordine di priorita': la prima che matcha vince.
CATEGORY_RULES = [
    ("Sindacati e associazioni di categoria",
        [r"\bsindacat\w*\b", r"\bconfederazion\w*\b", r"\bordine (?:dei|degli|nazionale)\b",
         r"\bassociazione\s+(?:nazionale|italiana)\s+(?:dei|degli|delle)?\s*(?:comuni|industria|categoria)",
         r"\bcamer[ae] penal\w*\b", r"\bunione italiana camere penali\b"]
        + [p for pats in ENTITIES_SINDACATI_CATEGORIA.values() for p in pats]),
    ("Autorità indipendenti/soggetti istituzionali",
        [r"\bminister[oa]\b", r"\bministr[oa]\b", r"\bautorit[aà]\b", r"\bagenzia\s+(?:nazionale|delle|per)",
         r"\bregione\b", r"\bprovincia\b", r"\bcomune di\b", r"\bprefett\w*\b", r"\bdipartimento\b",
         r"\bpresidenza del consiglio\b", r"\bprocura\b", r"\btribunale\b", r"\bgarante\b",
         r"\bcapo di stato maggiore\b", r"\bguardia di finanza\b", r"\bcarabinieri\b",
         r"\bpolizia (?:di stato|penitenziaria)\b", r"\bvigili del fuoco\b",
         r"\bconsiglio superiore della magistratura\b", r"\bcorte costituzionale\b",
         r"\bente nazionale\b", r"\bente pubblico\b", r"\bconsorzio di bonifica\b"]
        + [p for pats in ENTITIES_ISTITUZIONALI.values() for p in pats]),
    ("Aziende partecipate",
        [p for pats in ENTITIES_AZIENDE_PARTECIPATE.values() for p in pats]),
    ("Aziende",
        [r"\bs\.?p\.?a\.?\b", r"\bs\.?r\.?l\.?\b", r"\bazienda\b"]),
    ("Associazioni e organizzazioni della società civile",
        [r"\bassociazion\w*\b", r"\bfondazion\w*\b", r"\bonlus\b", r"\bong\b", r"\bcomitato\b",
         r"\bmovimento\b", r"\blegambiente\b", r"\bwwf\b", r"\blav\b", r"\bcittadinanza\s*attiva\b",
         r"\bunicef\b", r"\bamnesty international\b", r"\bsave the children\b", r"\bconsumatori\b",
         r"\baltroconsumo\b", r"\bfederconsumatori\b"]),
    ("Esperti/Professori/Professionisti",
        [r"\bprofessor\w*\b", r"\bdocente\b", r"\bricercatore\b", r"\bavvocato\b",
         r"\buniversit[aà]\b", r"\bgiornalista\b", r"\besperto\b", r"\bdottor\w*\b"]),
]

_COMPILED_RULES = [(cat, [re.compile(p, re.IGNORECASE) for p in pats]) for cat, pats in CATEGORY_RULES]
_COMPILED_ENTITIES = {name: [re.compile(p, re.IGNORECASE) for p in pats] for name, pats in KNOWN_ENTITIES.items()}


def classify_category(title: str) -> str:
    for cat, patterns in _COMPILED_RULES:
        for p in patterns:
            if p.search(title):
                return cat
    return "Altro"


def find_known_entities(title: str):
    found = []
    for name, patterns in _COMPILED_ENTITIES.items():
        for p in patterns:
            if p.search(title):
                found.append(name)
                break
    return found
