# Dinoer — Spickzettel

Version 1.23.0 — August 2026

Alles auf einer Seite. Vollständige Referenz: `docs/MANUEL.md`.

---

## Drei Befehle

```bash
# Eine Seite sehen: Accessibility-Baum
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url URL --a11y

# Ein Szenario ausführen
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py --scenario DATEI.json

# Eine Szenario-Referenz lesen und vergleichen (strukturelle Überwachung)
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario DATEI.json --replay-verifier REF.json
```

Der erste Aufruf auf einer Maschine benötigt `--guide-version X.Y`, zu
lesen mit `grep notice-version /opt/dinoer/docs/GUIDE_LLM.md`.

---

## Die Schleife

```
        Sie entscheiden, was als Nächstes zu tun ist
                  │
                  ▼
   ┌──────────────────────────────┐
   │  shot.py / rpa.py            │   ein Prozess, ein JSON auf stdout
   │    ├─ Chromium (headless)    │
   │    ├─ A11y: Seitenstruktur   │
   │    └─ secrets: füllt Credentials aus│   nie in der Shell, nie in einem Log
   └──────────────┬───────────────┘
                  │  boussole + JSON
                  ▼
        Sie lesen denselben Zustand,
        den auch der Betreiber sehen kann
```

Der Sitzungszustand lebt in einer Datei, nicht im Prozess: ein zweiter
Aufruf mit `--reprendre-session` nutzt Cookies wieder — nie den
DOM-Zustand.

---

## Die Ausgabe in dieser Reihenfolge lesen

| Lesen | Sagt Ihnen |
|---|---|
| `succes` | ob der Lauf abgeschlossen wurde |
| `boussole.url_courante` | wo Sie tatsächlich gelandet sind |
| `boussole.dernier_code_http` | Status der letzten Navigation |
| `etat.pret_a_agir` + `etat.raisons` | wahrgenommene Friktionen — ein Bericht, nie eine Schranke |
| `a11y_tree` | Seitenstruktur — Überschriften, Felder, Schaltflächen |
| `respect` | Ihr eigener Fußabdruck: Seiten, Aktionen, Dauer |

Stimmt `boussole` nicht mit Ihrer Erwartung überein: vor jeder mutierenden
Aktion anhalten.

---

## Jede Aktion

`type` ist immer erforderlich. Die folgenden Schlüssel sind die
zusätzlichen.

| Aktion | Erforderlich | Optional |
|---|---|---|
| `naviguer` | `url` | — |
| `cliquer` | `selecteur` | `force`, `repli_js` |
| `cliquer_iframe` | `iframe_selecteur` \| `iframe_chemin`, `selecteur` | `force` |
| `remplir` | `selecteur`, `valeur` | `secret_cle` |
| `remplir_iframe` | `iframe_selecteur` \| `iframe_chemin`, `selecteur`, `valeur` | `secret_cle` |
| `evaluer` | `script` | `attendu` \| `contient` \| `motif` |
| `extraire_texte` | — | — |
| `defiler` | `px` \| `selecteur` | — |
| `pause` | `ms` | — |
| `attendre` | `selecteur` | — |
| `attendre_selecteur_present` | `selecteur` | — |
| `attendre_absence` | `selecteur` | `delai_initial_ms` |
| `attendre_navigation` | — | — |
| `attendre_url` | `motif` | `attendre_changement` |
| `attendre_reseau_calme` | — | `timeout_ms` |
| `attendre_mfa_ntfy` | `selecteur` | `timeout` |
| `nettoyer_overlay` | `selecteur` | — |
| `declencher_scenario` | `scenario` | — |

---

## Credentials — die einzig korrekte Form

```json
{"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"}
```

Nie ein Secret in die Shell extrahieren. `lib/repertoire_chiffre.py` löst es
innerhalb des Playwright-Prozesses auf; der Wert erreicht nie Ihre
Kommandozeile, Ihre History oder ein Log.

---

## Wenn sich etwas sperrt

| Symptom | Versuchen |
|---|---|
| Klick läuft in Timeout, Element visuell verborgen | `"force": true`, dann `"repli_js": true` |
| Element unterhalb des sichtbaren Bereichs | zuerst `defiler` |
| Seite wird nie fertig geladen | `--wait-until load` |
| Absenden bewirkt nichts, kein Fehler | native HTML-Validierung — Formular über `evaluer` absenden |
| `exit 42` | verschlüsseltes Verzeichnis nicht gemountet (`bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh`), oder Prüfsumme der Credentials ungültig (Credentials-Datei prüfen) — beides `SecretsFermesError` |
| `guide_non_lu` | einmalig `--guide-version` übergeben |
| 403 / 429 | `respect.waf_bloquants` lesen — ein Signal, keine Ausnahme |

---

## Exit-Codes

`0` Erfolg · `1` Ausführung fehlgeschlagen oder Assertion fehlgeschlagen · `2` Ungültige Argumente (abgelehnt, bevor ein Browser gestartet wurde) · `3` Falscher Interpreter – verwenden Sie die venv (`/opt/dinoer/venv/bin/python`) · `42` Verschlüsselter Credential-Verzeichnis geschlossen oder Prüfsumme der Credentials ungültig (`SecretsFermesError` Familie) · `43` Keine `secrets_dir` konfiguriert (`SecretsNonConfigureError`).
