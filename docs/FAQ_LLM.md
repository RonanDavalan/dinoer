# Dinoer — FAQ for LLMs

Version 1.10 — August 2026 (v1.23.0) — surface realigned to the Dinoer
reconstruction: no screenshot, no Set-of-Mark, no vision model. The agent
reads `a11y_tree` and `evaluer` values.

Answers to technical questions raised by language models during real Dinoer sessions.
No attribution — these are recurring questions, not individual testimonies.

---

## Getting started

### Q: I got `"erreur": "guide_non_lu"` and exit 1 before anything ran — what happened?

**You have not proven you read `docs/GUIDE_LLM.md` yet (v1.18.0+).**

`shot.py` and `rpa.py` both refuse to launch Playwright without
either `--guide-version X.Y` (the `<!-- notice-version: X.Y -->` value found
on line 3 of `docs/GUIDE_LLM.md`) or a local marker from a previous accepted
call. This is deliberate, not a bug — field observation showed models calling
Dinoer without reading anything first, hitting avoidable errors, and only
reading the guide after the fact. See `docs/RADAR_MODELES.md` for the
incident that motivated it.

```bash
cat /opt/dinoer/docs/GUIDE_LLM.md
# read it, find "<!-- notice-version: X.Y -->" near the top, then:
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url <url> --guide-version 1.3
```

You will not be asked again on this machine, as this OS user, until
`GUIDE_LLM.md`'s `notice-version` changes.

### Q: How do I check which Dinoer version is installed, without a full run?

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --version
# → {"outil": "shot.py", "version": "1.23.0"}
```

No Playwright launch, no `--url` needed, exit 0 immediately (v1.18.0+). Same
flag on `rpa.py`. Distinct from `--guide-version` — one reports
the Dinoer release, the other proves you read the guide. Passing one where
the other is expected fails.

---

## Perception

### Q: What is in the `boussole` object?

The `boussole` is the first object to read in any Dinoer JSON output. It
always contains the run's identity and the page it actually reached:

```json
"boussole": {
  "utilisateur": "operator",
  "ip_locale": "__IP_LAN__",
  "repertoire": "/opt/dinoer",
  "operation_id": "a1b2c3d4e5f6",
  "url_courante": "https://target.local/dashboard",
  "titre_page": "Dashboard — My App",
  "dernier_code_http": 200
}
```

Conditional keys appear only when the corresponding mechanism is active:

| Key | Present when |
|---|---|
| `auth_status` | `--auth-indicator` active (`"active"` or `"inactive"`) |
| `session_derive` | `--reprendre-session` active and URL diverged |
| `stealth_actif` | `--stealth` active and applied successfully (v1.15.0) |
| `wait_until` | the effective wait model differs from the default (v1.22.0) |
| `http_credentials_actif` | HTTP Basic Auth credentials present and no 401 occurred |
| `http_auth_requise` | the target answered 401, a challenge is pending |
| `tls_errors_ignored` | `--ignore-tls-errors` active |
| `waf_ignore_actif` | `--ignorer-waf` active |
| `repli_js_utilise` | a `repli_js` JS click escalation actually fired |
| `filtre_evaluer_actif: false` | `--no-filtre-evaluer` active (debug runs only) |
| `a11y_redaction_echouee` | the a11y-tree secret redaction failed for one node |

`titre_page` is always present but may be empty (`""`) on `about:blank` or if Playwright
cannot read the title before closing. `operation_id` (v1.16.0) uniquely identifies the
run and names its temporary-file directory under `/tmp/dinoer/<operation_id>/`.

The JSON root also carries a deterministic `etat` object (`pret_a_agir`,
`niveau_confiance`, `raisons`, v1.16.0) synthesizing these signals into one
go/no-go read — see `docs/MANUEL.md` section 2d.

### Q: Does `etat.pret_a_agir: false` block my next action?

**No. `etat` is a report, not a gate — Dinoer never checks it before running
an action.**

No verb dispatcher reads `pret_a_agir`. Seeing `false` means Dinoer perceived
a friction worth your attention (a probable WAF block, JS/console errors, a
navigation cap reached, a session drift) before you act — it is descriptive,
not a permission system. The decision to stop, investigate `raisons` further,
or proceed with the mutating action you had planned always belongs to you.

This is worth asking explicitly because `etat`'s shape — three confidence
levels, a boolean readiness flag — reads like a gate at a glance, even though
it functions as a synthesis of signals already present elsewhere in the JSON
(`auth_status`, `respect.plafond_atteint`, `derive_session`, `erreurs_js`,
`erreurs_console`, WAF detection). If you find yourself refusing to act
purely because the flag is `false`, without having read `raisons` first, you
are treating a signal as an authority it does not have.

### Q: Is `boussole` present in every output?

**Yes** — `boussole`, `url_courante`, `titre_page` and `dernier_code_http`
(v1.14.0, extended v1.22.0) are always present after a completed run. Dinoer
has no capture path, so there is no question of a key dropping because a
PNG was skipped: reading state **is** the output.

| Key | Always in a successful run? |
|---|---|
| `boussole` (incl. `url_courante`, `titre_page`, `dernier_code_http`) | Always |
| `a11y_tree` | Only with `--a11y` |
| `evaluations` | Only if `evaluer` actions ran |
| `extraction_texte` | Only if `extraire_texte` ran |
| `etat` | Always (descriptive) |
| `latences_actions` | Always (v1.20.0) |

### Q: What about iframes — are they supported?

**Yes, via `cliquer_iframe`/`remplir_iframe` (v1.17.0), including cross-origin.
There is no Set-of-Mark to be aware of: target frames and elements by explicit
CSS selector.**

Cross-origin iframes: JS injection cannot cross the Same-Origin Policy boundary
by construction — a hard browser security limit, not a Dinoer gap. Since v1.17.0,
`cliquer_iframe` and `remplir_iframe` bypass this via Playwright's native
`page.frame_locator()` (CDP-based, not JS injection):

```json
{"type": "cliquer_iframe", "iframe_selecteur": "iframe#paiement", "selecteur": "button.valider"},
{"type": "remplir_iframe", "iframe_selecteur": "iframe#paiement", "selecteur": "input[name=cvv]", "valeur": "depuis_secrets", "secret_cle": "cvv"}
```

`remplir_iframe` supports `depuis_secrets` exactly like `remplir` — never a
plaintext credential in the scenario.

**Nested iframes (v1.18.0):** replace `iframe_selecteur` with `iframe_chemin`,
an ordered array of selectors, one per nesting level:

```json
{"type": "cliquer_iframe", "iframe_chemin": ["iframe#wrapper", "iframe#paiement"], "selecteur": "button.valider"}
```

`iframe_selecteur` and `iframe_chemin` are mutually exclusive — exactly one
required per action.

**Shadow DOM:** Dinoer does not number elements inside shadow roots. Reach
them with `evaluer` (JS operates per-document, shadow roots included) or by
giving the application stable CSS selectors.

---

## Scenarios and validation

### Q: Is there a dry-run or pre-validation mode?

**Partial — since v1.9.2.**

`rpa.py` runs a static validator **before launching Playwright**:

**Schema validation** (`jsonschema`) — checks action types, required keys, and
rejects unknown properties. Requires `jsonschema` in the venv:

```bash
/opt/dinoer/venv/bin/pip install jsonschema
```

A full dry-run (resolving `depuis_secrets`, validating CSS selectors on a live DOM)
would require Playwright and is not yet implemented. The schema validator catches the most
common authoring errors without browser overhead.

### Q: Can a scenario call another scenario?

**Yes — since v1.9.2, via `declencher_scenario`.**

```json
{
  "url": "https://target.local/dashboard",
  "actions": [
    {"type": "declencher_scenario", "scenario": "login"},
    {"type": "cliquer", "selecteur": "button.continue"}
  ]
}
```

`rpa.py` inlines the sub-scenario's actions before calling Playwright — the browser
runs a single continuous session. The credentials and journal are managed by the parent run.

- Sub-scenario resolved via: `scenarios/<name>{.json,.yaml,.yml}` or absolute path.
- Recursion depth capped at 5 levels. Circular references produce a structured
  `profondeur_max_chainages` error.
- Schema validation runs on the **full flattened action list** (parent + all sub-scenarios
  inlined) before any Playwright call.

---

## Versions

### Q: Which version introduced which feature?

| Feature | Version |
|---|---|
| RPA scenarios (`rpa.py`), encrypted credentials | v1.5 |
| Scroll (`defiler`), skills, TOTP, ntfy MFA | v1.6 |
| Wait primitives, `nettoyer_overlay`, vector memory | v1.8 / v1.9 (internal) |
| `--auth-indicator` / `auth_status` (S-1) | v1.9.0 |
| `declencher_scenario` | v1.9.2 |
| `dinoer.conf`, `SecretsNonConfigureError` (exit 43) | v1.9.3 |
| `--secrets` multiple credentials files, fail-fast venv | v1.10.0 |
| `force: true` on `cliquer`, assertions `contient`/`motif` | v1.11.0 |
| Error routing table, notice versioning, secret blurring | v1.12.0 |
| Enriched `boussole` (`url_courante`, `titre_page`), `--auth-indicator-negative` | v1.14.0 |
| Scenario neutralisation doctrine, `password` fields require `depuis_secrets` | v1.14.1 |
| Respectful Navigation: `--stealth`, courtesy delays, navigation caps, `respect` metrics, `SecretsChecksumError` | v1.15.0 |
| Security hardening: `--no-evaluer`, journal permissions, URL scheme validation, `--ignore-tls-errors` | v1.15.1 |
| `etat` deterministic verdict, `operation_id`, passive WAF signal, `erreurs_console` | v1.16.0 |
| `--replay-verifier`, `--checkpoint`, `cliquer_iframe`/`remplir_iframe` | v1.17.0 |
| Refined WAF heuristic + `--ignorer-waf`, checkpoint navigation-cap fix | v1.17.2 |
| Mandatory `--guide-version`/`--version` pre-flight lock, nested iframes (`iframe_chemin`), `scripts/monitor-verifier.sh` | v1.18.0 |
| `chainage` traceability for `declencher_scenario`, `etat` clarified as declarative | v1.19.0 |
| `journal.py --erreurs` filter, `latences_actions` per-action timing | v1.20.0 |
| `--http-credentials` (HTTP Basic Auth, origin-scoped), non-presumption rule | v1.21.0 |
| `repli_js` JS click escalation, `dernier_code_http` in boussole, `--wait-until` for never-idle targets, **breaking: `citoyennete` output key renamed `respect`** | **v1.22.0** |

**Current stable version: v1.23.0.**

The operation log (`/var/log/dinoer/operations.jsonl`) and the friction index
(`docs/RETOUR_EXPERIENCE.md`) cover the full history from v1.0 — see that
file directly for the current friction count rather than a number
duplicated here, which would otherwise need updating every cycle.

---

## See also

- `docs/GUIDE_LLM.md` — complete operator guide (security rules, all flags, all actions)
- `docs/GUIDE_EXPLORATION.md` — how to explore an unknown interface with Dinoer
- `docs/RETOUR_EXPERIENCE.md` — terrain frictions and resolutions
- `docs/RADAR_MODELES.md` — observed LLM behaviour on real Dinoer sessions