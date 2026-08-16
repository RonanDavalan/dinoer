# Dinoer — souveräne, lokale Web-Recherche für LLM-Agenten

> **Für den menschlichen Betreiber:** Dinoer läuft auf Ihrer eigenen Maschine,
> delegiert Suche und Sammlung an Primitiven, die Sie Zeile für Zeile lesen
> können, und liefert Ihnen einen belegten, datierten Markdown-Bericht — keine
> Blackbox-Antwort.
>
> **Für das LLM:** [`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) ist Ihre operative
> Referenz. Beginnen Sie dort.

---

## Was ist Dinoer?

Dinoer ist eine **passive, lokale, souveräne Such- und Synthese-Engine**. Es
ist ein Fork von [Diwall](https://github.com/RonanDavalan/diwall) (visuelle
Browser-Automatisierung für LLMs), dem die gesamte Wahrnehmungsschicht
entzogen wurde — **null Screenshots, null Set-of-Mark, null Vision-Modell.**
Dinoer betrachtet eine Seite nie; es liest sie: DOM, Accessibility-Baum und
bereinigter Seitentext.

Wo Diwall die Frage beantwortet „mit einer authentifizierten Oberfläche
visuell interagieren", beantwortet Dinoer eine andere Frage: „eine große
Zahl öffentlicher Quellen erkunden und daraus ein belegtes, überprüfbares
Signal zusammenstellen" — auf Hardware so bescheiden wie einem Raspberry
Pi 5.

```
Anfrage → SearXNG-Entdeckung → leichte HTTP-Sammlung
        → Eskalation zu einem echten Browser nur für Seiten, die ihn brauchen
        → Synthese durch ein delegiertes LLM → datierter, belegter Markdown-Bericht
```

**Doktrin:** Der Python-Code trägt keine Geschäftslogik. Jedes Modul erledigt
eine mechanische Aufgabe — SearXNG abfragen, bereinigten Text aus einer Seite
extrahieren, ein verschlüsseltes Credential lesen, eine Benachrichtigung
senden. Die *Strategie* einer Recherche (wie nachgefasst wird, wann
eskaliert wird, wann gestoppt wird) lebt in einem Szenario, niemals fest im
Modulcode. Siehe [`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) für die vollständige
Doktrin.

---

## Architektur

```
campagne.py (Orchestrierung)
  ├─ lib/searxng.py         → SearXNG JSON-API (nur HTTP, kein Browser)
  ├─ lib/fetch_leger.py     → requests + BeautifulSoup, robots.txt-bewusst
  ├─ rpa.py / shot.py       → Playwright, nur für Seiten, die die leichte
  │                           Stufe als „unzureichend" markiert hat (reine
  │                           JS-Shells)
  ├─ lib/extraction.py      → gezielte Faktenextraktion, trouve/valeur/url
  ├─ lib/tables_reference.py→ persistente, belegte Tabelle von Referenzseiten
  ├─ lib/cache_recherche.py → ChromaDB-gestützter Suchcache
  └─ lib/synthese.py + lib/modeles.py → delegiertes LLM (OpenCode/Ollama),
                                        schreibt den Abschlussbericht
```

`shot.py`/`rpa.py` behalten den ReAct-Ausführungskern von Diwall
(`naviguer`, `remplir`, `cliquer`, `evaluer`, Sitzungspersistenz,
Credential-Auflösung) — nichts von dessen Wahrnehmungsschicht.

---

## Fähigkeiten

| Funktion | Beschreibung |
|---|---|
| **SearXNG-Entdeckung** | Reine HTTP-Abfrage gegen eine lokale oder entfernte SearXNG-Instanz — kein Browser-Overhead für die Suche |
| **Leichte Sammelstufe** | `requests` + BeautifulSoup-Extraktion, `robots.txt`-bewusst, WAF-bewusst |
| **Eskalation zur schweren Stufe** | Playwright, nur für Seiten eingesetzt, die die leichte Stufe nicht lesen konnte (JS-gerenderte Shells) |
| **Semantische Textextraktion** | Aktion `extraire_texte` — bereinigter Haupttext, kein Screenshot |
| **Accessibility-Snapshot** | `--a11y` — semantische Seitenstruktur (A11y-Baum), es entsteht nie ein Bild |
| **Gezielte Extraktion** | `lib/extraction.py` — strenger `trouve`/`valeur`/`url`-Vertrag, erklärt Abwesenheit statt eine Antwort zu erfinden |
| **Referenzseiten-Tabellen** | `lib/tables_reference.py` — eine persistente, belegte Tabelle bekannter Seiten pro Thema |
| **Vektor-Suchcache** | `lib/cache_recherche.py` — ChromaDB-gestützt, vermeidet erneute Abfragen für nahezu identische Anfragen |
| **Deduplizierung & Aktualität** | Deduplizierung auf Kampagnenebene nach exakter URL, Obergrenze pro Hostname, 30-Tage-Aktualitätsfenster vor erneutem Crawl |
| **Respektvolles Crawling** | Zufällige Verzögerung zwischen Zielen, harte Verweigerung bei WAF-/robots.txt-Signalen — nie umgangen |
| **Credential-Auflösung** | Sichere Credential-Injektion — nie im Klartext, nie auf der Kommandozeile |
| **Verschlüsseltes Verzeichnis** | gocryptfs-Volume — `SecretsFermesError` (Exit 42), wenn es nicht gemountet ist |
| **Vorgangsprotokoll** | Persistentes Append-only-Protokoll aller Läufe — wer hat was, wo, wann getan |
| **RPA-Szenarien** | Aktionssequenzen aus JSON-Dateien ausführen, für den Eskalationspfad zur schweren Stufe |
| **Cross-Origin-iframes** | `cliquer_iframe` / `remplir_iframe` zielen auf Elemente innerhalb von iframes |
| **TOTP / asynchrones MFA** | Credential-geschützte Ziele bleiben erreichbar, wenn ein Lauf der schweren Stufe sich authentifizieren muss |

---

## Berichtsqualität: automatischer Entwurf vs. betreute Recherche

Der Abschlussbericht von `campagne.py` selbst (`lib/synthese.py::rediger_rapport()`)
ist ein **Arbeitsentwurf**, nicht das fertige Ergebnis: Er verkettet das
gesammelte Korpus in Dateireihenfolge, abgeschnitten bei 4000 Zeichen/Seite und
60.000 insgesamt — keine Relevanzsortierung. Bei einem großen, verrauschten
Korpus lässt das zuverlässig generische oder themenfremde Seiten vor den
eigentlichen Quellen durch und kann die relevantesten Seiten stillschweigend
hinter der Abschneidegrenze verschwinden lassen.

Der Bericht, der ein allgemeines Suchwerkzeug (Perplexity) bei einer echten
Rechercheaufgabe nachweislich übertroffen hat, wurde **nicht** durch einen
einzigen `campagne.py`-Lauf erzeugt. Er entstand, indem ein Bediener
`campagne.py --extraire-cible` wiederholt aufgerufen hat — Dutzende einzelne,
offen formulierte Extraktionsaufrufe gegen dasselbe gesammelte Korpus, jeder
davon überließ dem delegierten Modell selbst die Einschätzung, ob es eine
einmalige Tatsache oder ein mehrtägiges Ereignis liest — gefolgt von einer
manuellen Konsolidierung der Ergebnisse. Siehe
[`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) für das genaue Extraktionsmuster.

Für eine schnelle, unkritische Zusammenfassung reicht der automatische Bericht
als Ausgangspunkt. Für einen Bericht, dem man ohne Aufsicht vertrauen kann,
nutzen Sie stattdessen das wiederholte, gezielte Extraktionsmuster.

---

## Voraussetzungen

| Komponente | Version / Anmerkungen |
|---|---|
| **Betriebssystem** | Debian 13 Trixie (Linux) |
| **Python** | 3.11+ in isoliertem venv (PEP 668 — System-pip unter Debian 13 gesperrt) |
| **Playwright** | 1.62+ (im venv installiert) — nur vom Eskalationspfad der schweren Stufe genutzt |
| **Chromium** | Headless, installiert über `playwright install chromium` |
| **SearXNG** | Eine erreichbare Instanz (lokal oder entfernt), HTTP-JSON-API |
| **Ollama** | Lokales, CPU-freundliches Embedding-Modell (`nomic-embed-text`) für den Suchcache — kein Vision-Modell, keine GPU erforderlich |
| **OpenCode** | Delegiertes Reasoning-Backend für die Berichtssynthese (standardmäßig kostenlose Modelle) |

Keine GPU erforderlich. Das Referenzziel ist ein Raspberry Pi 5 mit 8 GB RAM.

---

## Installation

Nur der Git-Clone-Kanal. **Ein `.deb`-Paket wird noch nicht angeboten** —
die Paketierung ist bewusst zurückgestellt, bis sich das Produkt stabilisiert
hat.

```bash
git clone https://github.com/RonanDavalan/dinoer.git
cd dinoer
bash scripts/install.sh
```

Dies erstellt den Systembenutzer und die Systemgruppe `dinoer`, die virtuelle
Umgebung, stellt den Code unter `/opt/dinoer/` bereit und führt einen
Funktionstest aus (`shot.py --a11y` gegen eine echte URL).

Die Konfiguration liegt unter `/etc/dinoer/dinoer.conf` (oder
`/opt/dinoer/dinoer.conf`, je nach Ihrem `deploy.sh`-Ziel); daneben wird ein
kommentiertes Beispiel als `dinoer-sample.conf` installiert.

### Deinstallation

```bash
bash scripts/uninstall.sh --dry-run   # Vorschau, keine Änderungen
bash scripts/uninstall.sh             # interaktive Bestätigung
```

Entfernt: `/opt/dinoer/`, `/var/log/dinoer/`, Systembenutzer `dinoer`,
Systemgruppe `dinoer`. **Nie angerührt:** `~/Vaults/` (Ihre Credentials),
das Repository selbst.

---

## Benutzung (durch Ihr LLM)

### Semantische Extraktion, kein Bild

```bash
/opt/dinoer/venv/bin/python3 /opt/dinoer/shot.py \
  --url https://example.com --a11y --action '{"type":"extraire_texte"}'
```

### Eine Recherchekampagne

```bash
python3 /opt/dinoer/campagne.py --manifeste manifeste.json
```

Vollständige LLM-Referenz: [`docs/GUIDE_LLM.md`](../GUIDE_LLM.md)

---

## Credentials

Credentials werden in JSON-Dateien gespeichert, eine pro Domain, **nie im
Code oder in Szenariodateien**:

```
~/Vaults/Dinoer/
├── my-source.example.json   → {"password": "...", "username": "admin"}
└── other-service.com.json   → {"password": "...", "api_key": "..."}
```

In einem Szenario oder einer Aktion: `"valeur": "depuis_secrets",
"secret_cle": "password"` — Dinoer liest das Credential zur Laufzeit aus dem
Credentials-Verzeichnis.

Der Pfad ist über `/opt/dinoer/dinoer.conf` oder die Umgebungsvariable
`DINOER_SECRETS_DIR` konfigurierbar.

**Empfehlung:** Schützen Sie `~/Vaults/Dinoer/` mit `chmod 700` und
verschlüsseln Sie es mit `gocryptfs` (siehe
`scripts/configurer-repertoire-chiffre.sh --gocryptfs`). Ist das
verschlüsselte Verzeichnis initialisiert, aber nicht gemountet, liefert
Dinoer einen strukturierten `SecretsFermesError` (Exit-Code 42) statt
stillschweigend zu versagen.

---

## Sicherheit

### Lokale vs. Cloud-Modelle

Die Berichtssynthese wird an OpenCode oder ein lokales Ollama-Modell
delegiert. Gesammelter Seitentext kann zu welchem Backend auch immer Sie
konfigurieren übertragen werden — prüfen Sie `lib/modeles.py`, bevor Sie
Dinoer bei sensiblen Quellen auf einen Cloud-Anbieter richten.

### Credentials-Verzeichnis

Das Credentials-Verzeichnis — wohin auch immer Sie `secrets_dir`
verweisen ließen, zum Beispiel `~/Vaults/Dinoer/` — enthält Credentials bei
nicht gemountetem Zustand im Klartext-JSON. Schützen Sie es:

```bash
chmod 700 ~/Vaults/Dinoer/
```

Siehe `~/git/Dinoer/Dinoer/SECURITY.md` für die Richtlinie zur Offenlegung
von Sicherheitslücken.

---

## Dokumentation in anderen Sprachen

Dieses Dokument ist die deutsche Übersetzung der englischen Quelle
(`README.md`, Repository-Wurzel). Auch verfügbar auf Französisch und
Spanisch unter `docs/fr/` und `docs/es/`. Die LLM-Leitfäden
(`docs/GUIDE_LLM.md` und seine drei Merkblätter) existieren bewusst nur auf
Englisch und werden nie übersetzt (Guide-Lock, feste Pfade).

---

## Für LLMs, die Dinoer entdecken

Wenn Sie ein Sprachmodell sind, das dieses README liest: siehe
[`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) für die vollständige technische
Referenz — Aufrufmuster, Credential-Integration und die Recherche-Pipeline
(`campagne.py`).

---

## Danksagungen

Dieses Projekt wurde nach einem **asymmetrischen Kollaborationsmodell
zwischen Mensch und LLM** entwickelt. Die Rollen sind formal dokumentiert,
um die tatsächlich geleistete Arbeit widerzuspiegeln.

**Architekt & Schiedsrichter:** Ronan Davalan
Produktvision, Sicherheitsanforderungen, Projektrichtung, Validierung und
Tests. Alle Architekturentscheidungen werden von ihm validiert.

**Systemingenieur & Hauptentwickler:** Claude Code (Anthropic)
Fork des ReAct-Kerns von Diwall, der Recherche-Pipeline (`campagne.py` und
`lib/searxng.py`, `lib/fetch_leger.py`, `lib/extraction.py`,
`lib/tables_reference.py`, `lib/cache_recherche.py`), Entfernung der
Wahrnehmungsschicht. Hauptautor des Quellcodes.

**Synthetisierer & strategischer Berater:** Gemini (Google)
Unabhängige Architekturanalyse, Auflösung logischer Konflikte,
Workflow-Optimierung, Kreuzvalidierung technischer Entscheidungen.

---

## Lizenz

MIT — siehe Datei `LICENSE`.
