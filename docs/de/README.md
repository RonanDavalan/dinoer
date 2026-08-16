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

## Positionierung: Worauf Dinoer setzt und worauf nicht.

Dinoer konkurriert nicht mit generellen Suchassistenten (wie Perplexity und ähnlichen) hinsichtlich der Breite, des Umfangs oder des Preises bei der Informationsbeschaffung. Ein echter Test (14. August 2026, Reputationsforschung zu einem realen Thema) hat dies direkt gemessen, anstatt es nur anzunehmen: Von den 28 Seiten, die durch Dinoers eigene, von SearXNG gesteuerte Suchfunktion gefunden wurden, waren drei Quellen, die eine einfache, nicht vorbereitete Perplexity-Abfrage sofort lieferte (ein LinkedIn-Profil, eine Projektseite, ein Stockfoto-Hinweis), vollständig abwesend – dies war auf SearXNG-Abfragen zurückzuführen, die nach der falschen Art von Suchergebnissen suchten (Unternehmensverzeichnisse, nicht den Begriffen, die diese Seiten hätten liefern können), und nicht auf einen Ranking- oder Kürzungsmangel im weiteren Verlauf. Ein generischer Such-Backend mit authentifizierten, cookie-basierten Engines dahinter hat eine strukturelle Reichweite, die eine nicht authentifizierte lokale SearXNG-Instanz nicht besitzt.

Was derselbe Test auf demselben Korpus verifiziert hat, misst eher als dass er etwas annimmt: **eine nachvollziehbare, reproduzierbare Synthese eines fixierten Korpus.** Jede Aussage in einem Dinoer-Bericht ist einer bestimmten Seite zuzuordnen, die tatsächlich auf die Festplatte geschrieben wurde (`collecte.jsonl`/`operations.jsonl`) – ohne jegliche Abhängigkeit von dem, was ein Such-Backend eines Drittanbieters während der Generierung der Antwort getan hat. Eine direkte Überprüfung des gesamten Ereignisstroms des delegierten Modells während der Synthese (nicht nur seines endgültigen Textes) bestätigte, dass während der Berichtserstellung keine externen `websearch`/`webfetch` Aufrufe den Korpus erreicht haben. Das ist das eigentliche Wertversprechen: genau zu wissen, woher eine Antwort stammt, und nicht mehr als ein allgemeines Tool liefern würde.

---

## Architektur

```
campagne.py (orchestration)
  ├─ lib/searxng.py         → SearXNG JSON API (HTTP only, no browser)
  ├─ lib/fetch_leger.py     → requests + BeautifulSoup, robots.txt-aware
  ├─ rpa.py / shot.py       → Playwright, only for pages the light tier
  │                           marked "insufficient" (JS-only shells)
  ├─ lib/selection_candidats.py → best-match pick among several fetched
  │                           candidates, "produit" targets only
  ├─ lib/extraction.py      → targeted fact extraction, trouve/valeur/url
  ├─ lib/tables_reference.py→ persistent, sourced table of reference sites
  ├─ lib/cache_recherche.py → ChromaDB-backed search cache
  └─ lib/synthese.py + lib/modeles.py → delegated LLM (OpenCode/Ollama),
                                        writes the final report
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

## Berichtsqualität: Automatisch generierter Entwurf vs. sorgfältige Recherche

`campagne.py`'s eigener Abschlussbericht
(`lib/synthese.py::construire_contexte()` erstellt und kürzt den Korpus,
`rediger_rapport()` verfasst anschließend den Text)
ist ein **Arbeitsentwurf**, nicht das fertige Ergebnis: er verkettet den
gesammelten Korpus in Dateireihenfolge, abgeschnitten bei 4000 Zeichen/Seite und 60.000
insgesamt – ohne Relevanzbewertung. Bei einem großen, verrauschten Korpus führt dies zuverlässig dazu, dass generische oder themenfremde Seiten vor den eigentlichen Quellen angezeigt werden, und kann stillschweigend die relevantesten Einträge hinter dem Abschneidepunkt auslassen.

Bei einer realen Forschungaufgabe (eine lokale Veranstaltungsliste, siehe "Positionierung" oben für eine Aufgabe, bei der das Ergebnis anders ausfiel), übertraf die Qualität des Berichts nachweislich ein allgemeines Suchwerkzeug (Perplexity) – aber dieser Bericht wurde **nicht** durch einen einzigen `campagne.py` Durchlauf erstellt. Er stammt von einem Operator, der `campagne.py --extraire-cible` verwendete – Dutzenden einzelner, offener Abfragen an denselben Datensatz, wobei jedes Mal das delegierte Modell selbst beurteilen konnte, ob es eine einmalige Tatsache oder ein mehrtägiges Ereignis las – gefolgt von einer manuellen Zusammenführung der Ergebnisse. Siehe [`docs/GUIDE_LLM.md`](../GUIDE_LLM.md) für das genaue Extraktionsmuster.

Wenn Sie eine schnelle, nicht kritische Zusammenfassung benötigen, ist der automatische Bericht ein guter Ausgangspunkt. Wenn Sie einen Bericht benötigen, dem Sie ohne Aufsicht vertrauen können, verwenden Sie stattdessen das gezielte, wiederholte Extraktionsmuster.

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

Zwei Kanäle, die sich gegenseitig ausschließen, wenn sie auf derselben Maschine verwendet werden.

**`.deb` package** — der normale Pfad, wenn Sie Dinoer unverändert verwenden möchten:

```bash
sudo apt install ./dinoer_1.0.0-1_all.deb
```

Installiert den Systembenutzer und die Gruppe `dinoer`, eine isolierte Python-virtuelle Umgebung, Chromium, die sechs `dinoer-*` Befehle und deren Handbücher in vier Sprachen. Pakete, Quellcode und Prüfsummen werden auf [dinoer.davalan.fr](https://dinoer.davalan.fr) veröffentlicht – siehe die Seite [Downloads](https://dinoer.davalan.fr/en/guides/downloads/) für Details, einschließlich der Bedeutung des `apt` Sandbox-Hinweises.

**Git clone** – wenn Sie den Code ändern möchten:

```bash
git clone https://github.com/RonanDavalan/dinoer.git
cd dinoer
bash scripts/install.sh
```

Dies erstellt den Systembenutzer und die Systemgruppe `dinoer`, die virtuelle
Umgebung, stellt den Code unter `/opt/dinoer/` bereit und führt einen
Funktionstest aus (`shot.py --a11y` gegen eine echte URL).

Die Konfiguration befindet sich in `/etc/dinoer/dinoer.conf` (Kanal [`.deb`]) oder
`/opt/dinoer/dinoer.conf` (git-clone-Kanal); eine Beispielkonfiguration wird daneben installiert, nämlich als `dinoer-sample.conf` – reines JSON, nicht kommentiert (korrigiert am 15./08/2026]:
JSON hat keine Kommentarsyntax, die Datei war nie kommentiert). Ausnahme: `campagne.py`
liest niemals `DINOER_CONF` oder den oben genannten git-clone-Pfad – es liest
`/opt/dinoer/dinoer.conf` fest codierte Werte und löst seine eigenen Pfade über spezielle
Umgebungsvariablen auf (`DINOER_CAMPAGNES_DIR`, `DINOER_SEARXNG_URL`,
`DINOER_TABLES_REFERENCE`, `DINOER_JOURNAL`).

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
`scripts/configurer-repertoire-chiffre.sh --gocryptfs` — nur Git-Clone-Kanal,
nicht vom `.deb` mitgeliefert; richten Sie auf diesem Kanal `gocryptfs`
selbst ein und zeigen Sie `secrets_dir` auf den gemounteten Pfad). Ist das
verschlüsselte Verzeichnis initialisiert, aber nicht gemountet, liefert
Dinoer eine strukturierte `SecretsFermesError` (Exit-Code 42), statt
stillschweigend zu scheitern.

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

**Systemingenieur & Lead-Entwickler:** Claude Code (Anthropic)
Abgeleitet vom ReAct-Kern von Diwall, der Forschungspipeline (`campagne.py` und
`lib/searxng.py`, `lib/fetch_leger.py`, `lib/selection_candidats.py`,
`lib/extraction.py`, `lib/tables_reference.py`, `lib/cache_recherche.py`),
Entfernung der Wahrnehmungsschicht. Hauptautor des Quellcodes.

**Synthetisierer & strategischer Berater:** Gemini (Google)
Unabhängige Architekturanalyse, Auflösung logischer Konflikte,
Workflow-Optimierung, Kreuzvalidierung technischer Entscheidungen.

---

## Lizenz

MIT — siehe Datei `LICENSE`.
