"""
Copia il template HTML e il JS in index.html/app.js al livello del progetto.

I dati (data/report_data.json, data/soggetti_index.json) NON sono piu'
iniettati inline: app.js li carica a runtime via fetch(). Questo richiede di
servire il progetto via http(s) (server locale o hosting come GitHub Pages);
aprendo index.html direttamente da filesystem (file://) il fetch fallisce
per le restrizioni CORS dei browser sui file locali.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_PATH = ROOT / "data" / "report_data.json"
SUBJECTS_PATH = ROOT / "data" / "soggetti_index.json"
TEMPLATE_PATH = Path(__file__).resolve().parent / "templates" / "report_template.html"
APP_JS_PATH = Path(__file__).resolve().parent / "templates" / "app.js"
OUT_PATH = ROOT / "index.html"
OUT_APP_JS_PATH = ROOT / "app.js"


def main():
    # valida che i dataset siano JSON corretti (non vengono copiati: restano in data/)
    json.loads(DATA_PATH.read_text(encoding="utf-8"))
    json.loads(SUBJECTS_PATH.read_text(encoding="utf-8"))

    OUT_PATH.write_text(TEMPLATE_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"Report scritto in {OUT_PATH}")

    OUT_APP_JS_PATH.write_text(APP_JS_PATH.read_text(encoding="utf-8"), encoding="utf-8")
    print(f"JS scritto in {OUT_APP_JS_PATH}")


if __name__ == "__main__":
    main()
