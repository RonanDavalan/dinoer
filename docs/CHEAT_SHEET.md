# Dinoer — cheat sheet

Version 1.23.0 — August 2026

Everything on one page. Full reference: `docs/MANUEL.md`.

---

## Three commands

```bash
# See a page: accessibility tree
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url URL --a11y

# Run a scenario
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py --scenario FILE.json

# Read a scenario reference and compare (structural monitoring)
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario FILE.json --replay-verifier REF.json
```

First call on a machine needs `--guide-version X.Y`, read with
`grep notice-version /opt/dinoer/docs/GUIDE_LLM.md`.

---

## The loop

```
        you decide what to do next
                  │
                  ▼
   ┌──────────────────────────────┐
   │  shot.py / rpa.py            │   one process, one JSON on stdout
   │    ├─ Chromium (headless)    │
   │    ├─ A11y: page structure   │
   │    └─ secrets: fills credentials│   never in the shell, never in a log
   └──────────────┬───────────────┘
                  │  boussole + JSON
                  ▼
        you read the same state
        the operator can see too
```

Session state lives in a file, not in the process: a second call with
`--reprendre-session` reuses cookies — never DOM state.

---

## Read the output in this order

| Read | Tells you |
|---|---|
| `succes` | did the run complete |
| `boussole.url_courante` | where you actually ended up |
| `boussole.dernier_code_http` | last navigation status |
| `etat.pret_a_agir` + `etat.raisons` | frictions perceived — a report, never a gate |
| `a11y_tree` | page structure — headings, fields, buttons |
| `respect` | your own footprint: pages, actions, duration |

If `boussole` does not match your expectation, stop before any mutating action.

---

## Every action

`type` is always required. Keys below are the additional ones.

| Action | Required | Optional |
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

## Credentials — the only correct form

```json
{"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"}
```

Never extract a secret into the shell. `lib/repertoire_chiffre.py` resolves it inside the
Playwright process; the value never reaches your command line, your history,
or any log.

---

## When something resists

| Symptom | Try |
|---|---|
| Click times out, element visually hidden | `"force": true`, then `"repli_js": true` |
| Element below the fold | `defiler` first |
| Page never finishes loading | `--wait-until load` |
| Submit does nothing, no error | native HTML validation — submit the form via `evaluer` |
| `exit 42` | encrypted directory not mounted (`bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh`), or credentials checksum invalid (inspect the credentials file) — both are `SecretsFermesError` |
| `guide_non_lu` | pass `--guide-version` once |
| 403 / 429 | read `respect.waf_bloquants` — a signal, not an exception |

---

## Exit codes

`0` success · `1` run failure or failed assertion · `2` invalid arguments (rejected
before any browser started) · `3` wrong interpreter — use the venv
(`/opt/dinoer/venv/bin/python`) · `42` encrypted credentials directory closed, or
credentials checksum invalid (`SecretsFermesError` family) · `43` no `secrets_dir`
configured (`SecretsNonConfigureError`).