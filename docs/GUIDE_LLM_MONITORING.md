# Dinoer — Monitoring guide (journal, state verdict, replay verifier, long ops)

<!-- notice-version: 1.4 -->
Version 1.4 — August 2026. Counts revisions of this notice, not releases of
Dinoer. Changed: absorbed the extraction recipe and synthesis-relevance
sections moved here from `GUIDE_LLM.md` to keep the index under budget.

Version 1.3 — August 2026. Notable in that text: full rewrite for the public
repo — the previous image-based monitoring surface (visual diffs, periodic
image captures, capture timeouts) was removed; replaced by the real
text/verdict surface (`respect`, `etat`, `erreurs_js`/`erreurs_console`,
`latences_actions`, `--replay-verifier`, journal). Honest note added: the
`mode_conseille` plumbing exists in code (`lib/journal.py::dernier_diagnostic_host`)
but is not wired into current output. Prior (v1.0/v1.1): `chemin_sensible_refuse`
error code, `latences_actions`, `journal.py --erreurs`.

Load this notice when: long-running operations, `--checkpoint`,
`--replay-verifier`, `--sauver-verifier-reference`, `mode_conseille`, journal,
`operations.jsonl`, `respect`/`etat` interpretation, navigation caps.

---

## Boussole JSON — key activation table

Every `shot.py`/`rpa.py` output includes a `boussole` object — read it first
(navigating state, not pixel state):

```json
"boussole": {
  "utilisateur": "operator", "ip_locale": "__IP_LAN__", "repertoire": "/opt/dinoer",
  "operation_id": "<uuid>", "url_courante": "https://target.local/dashboard",
  "titre_page": "Dashboard", "dernier_code_http": 200
}
```

| Key | Always? | Condition |
|---|---|---|
| `utilisateur` | always | OS user running the process |
| `ip_locale` | always | empty string if the outbound UDP probe fails |
| `repertoire` | always | working directory at invocation |
| `operation_id` | always | unified run identity — same value in the journal entry and the temp directory path |
| `url_courante` | always | final URL after navigation and actions |
| `titre_page` | always | empty string if `page.title()` fails |
| `dernier_code_http` | always | last navigation's HTTP status (v1.22.0) |
| `respect` | always | navigation-frugality ledger, see below |
| `session_derive` | conditional | `--reprendre-session` was used **and** the final URL diverged from the saved one |
| `auth_status` | conditional | `--auth-indicator` provided (`"active"`/`"inactive"`) |
| `stealth_actif` | conditional | `--stealth` genuinely active (real effect, not just the flag) |
| `tls_errors_ignored` | conditional | `--ignore-tls-errors` active |
| `waf_ignore_actif` | conditional | `--ignorer-waf` active |
| `repli_js_utilise` | conditional | the JS click escalation actually ran (real JS escalade, never just the flag) |
| `wait_until` | conditional | only when it differs from the default `networkidle` |
| `http_credentials_actif` | conditional | the Basic Auth challenge was actually resolved |
| `http_auth_requise` | conditional | a real 401 was hit |
| `filtre_evaluer_actif` | conditional | `false` only when `--no-filtre-evaluer` disabled the redaction filter |
| `champs_rediges` | conditional | count of fields redacted from output (secret resolution) |
| `a11y_redaction_echouee` | conditional | the a11y tree could not be built — honest failure, reported |

Do not assert the absence of a conditional key as a failure signal. Check
`auth_status` *value*, not its presence alone.

**Root vs `boussole` duplication:** `respect` appears at both the JSON root
and inside `boussole` — same object, two consumers (structured extraction vs
at-a-glance orientation). Do not treat them as independent signals.

---

## `respect` — the navigation-frugality ledger

```json
"respect": {
  "pages_visitees": 2,
  "actions_executees": 5,
  "duree_totale_ms": 18402,
  "plafond_atteint": "max_pages_par_run",
  "waf_bloquants": 1,
  "indice_agressivite": 0.2
}
```

| Field | Meaning |
|---|---|
| `pages_visitees` | number of pages visited (`max_pages_par_run` bound) |
| `actions_executees` | number of actions dispatched (`max_actions_par_run` bound) |
| `duree_totale_ms` | wall-clock time spent in the action loop |
| `plafond_atteint` | only if a navigation cap was hit — value is the cap name (both caps configured in `dinoer.conf`, section `[navigation]`; **defaults are non-zero and active even without a config file**: `min_action_delay_ms: 800`, `max_pages_par_run: 10`, `max_actions_par_run: 30`) |
| `waf_bloquants` | only if at least one navigation was flagged as WAF-blocked (403/429, or title/HTML keyword match) — a **signal, never an exception** |
| `indice_agressivite` | present whenever at least one action ran — ratio of mutating actions over total actions executed. Recommendation for open-ended exploration: keep it under 0.3 (30% writes). A high ratio during exploration signals the agent is mutating the target more than it is observing it — a matter of respect for the target, not a runtime-enforced cap. |

---

## `etat` — deterministic operational verdict (v1.16.0, item A)

Every successful `shot.py` run includes an `etat` object at the JSON root — a
pre-computed verdict synthesizing signals already present elsewhere, so you
don't cross-reference `auth_status`, `respect.plafond_atteint`,
`session_derive`, and `erreurs_js` by hand before deciding to proceed.

```json
"etat": {
  "pret_a_agir": true,
  "niveau_confiance": "eleve",
  "raisons": ["aucun signal de friction détecté"]
}
```

| Field | Type | Meaning |
|---|---|---|
| `pret_a_agir` | boolean | `false` if authentication is inactive, session drifted, a navigation cap was hit, or a WAF block was detected (and not overruled) |
| `niveau_confiance` | `"eleve"` \| `"modere"` \| `"faible"` | degrades to `modere` on non-blocking friction (JS/console errors, cap hit), to `faible` on auth/session problems, or `modere` on a WAF block ignored via `--ignorer-waf` (v1.17.2: no longer forces `pret_a_agir: false` on its own) |
| `raisons` | array of strings | one entry per contributing signal; `["aucun signal de friction détecté"]` when clean |

**Scope — what `etat` does NOT check:** it has no notion of your business
expectation for the page (is this the *right* URL, does the title match).
That is the job of `evaluer` + `contient`/`motif`/`attendu` assertions in
`rpa.py`. `etat` only aggregates signals `shot.py` can determine by itself.

**Honest note — `mode_conseille`:** the current documentation historically
described an `etat.mode_conseille` sub-object recommending a configuration
for the next call. The plumbing exists in code
(`lib/journal.py::dernier_diagnostic_host`, which looks up the latest
successful `diagnostic_dom.json` run for the same host), but it is **not
wired into the current output** — `_construire_etat` is called without the
`mode_conseille` argument in `shot.py::main()`. Treat any claim beyond this
notice as not confirmed in the running version.

**When absent:** `etat` is present only on the success path (`succes: true`).
On a failure, read `erreur` and `message` instead.

---

## Navigation caps — behavior after the limit (v1.15.2)

When `max_pages_par_run` or `max_actions_par_run` is reached, `shot.py`
closes the Chromium process cleanly (see `respect.plafond_atteint`). This
has consequences for state:

- **DOM state is destroyed** — open modals, unsubmitted form fields, scroll
  position are lost with the browser process.
- **Session state (cookies, `localStorage`) survives only if
  `--sauver-session` was explicit** on this run.
- **Resuming via `--reprendre-session` reloads the saved URL from scratch** —
  it does not replay DOM interactions since the save.
- **Dinoer does not interrupt itself** — there is no runtime timeout tied to
  these figures; they bound the run, they do not abort it mid-action
  unexpectedly.

**Planning:** submit data (forms, confirmations) *before* the caps are likely
to be reached. Only save session state where the DOM is stable (no open
modal, no pending submission). With `rpa.py --checkpoint`, a cap-stopped run
is treated as a partial section: the checkpoint is *updated* with actual
progress and you relaunch the same command to continue (fixed v1.17.2 — it
was previously deleted, silently losing progress).

### Duration thresholds — suspecting a stuck run

`respect.duree_totale_ms` measures wall-clock time in the action loop.
Indicative thresholds, not hard caps:

- **Under 60 000 ms:** normal for a simple run.
- **Above 120 000 ms:** suspect a redirect loop or network congestion.
  Self-impose a semantic stop rather than waiting further.

---

## `erreurs_js` vs `erreurs_console` — two distinct signals (v1.16.0, item D)

Both are root-level lists, always present (empty if nothing captured); both
feed `etat.niveau_confiance` (non-empty → degrades to `modere`):

| Field | Playwright source | Captures |
|---|---|---|
| `erreurs_js` | `page.on("pageerror", ...)` | uncaught JS exceptions (script crashes) |
| `erreurs_console` | `page.on("console", ...)`, filtered to `type == "error"` | `console.error(...)` calls and browser-level error-level console messages |

A page can log `console.error` for a failed API call without throwing —
`erreurs_js` stays empty while `erreurs_console` flags the friction. Read
both; neither substitutes for the other.

---

## `latences_actions` — per-action timing (v1.20.0)

Always present at the JSON root (empty list if no actions were passed). One
entry per action that actually dispatched — an action skipped because a
navigation cap was hit produces no entry, consistent with
`respect.actions_executees` not counting it either.

```json
"latences_actions": [
  {"index": 0, "type": "naviguer", "latence_ms": 842},
  {"index": 1, "type": "cliquer", "latence_ms": 63},
  {"index": 2, "type": "attendre_selecteur_present", "latence_ms": 1204}
]
```

Complements `respect.duree_totale_ms` (global): `latences_actions` breaks the
total per action, useful to spot which step is slow before reaching for a
longer `--timeout`.

---

## `dom_stats` — structural DOM counting

When available, a `dom_stats` object reports structural element counts:

```json
"dom_stats": {
  "boutons": 14, "inputs": 9, "listes_deroulantes": 2,
  "formulaires": 1, "liens": 41, "dialogues": 0
}
```

Counts are from a single JS evaluation (`boutons` = `button,
[role="button"], [role="menuitem"]`; `inputs` = `input:not([type="hidden"]),
textarea`; etc.). Useful as a cheap structural fingerprint and as input to a
`--replay-verifier` reference.

---

## `--replay-verifier` — structural non-regression (v1.17.0)

Compares a run's structural surface against a saved reference — CI-friendly,
no image, no LLM call.

```bash
# First run — save the reference
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario dashboard.json --sauver-verifier-reference ref.json

# Subsequent runs — compare
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario dashboard.json --replay-verifier ref.json
```

Verdict on stderr:
`{"type_comparaison": "replay_verifier", "verdict": "stable"|"regression", "diffs": [...]}`.
Exit 1 on `regression`; `diffs` lists each mismatched field with `reference`
vs `obtenu`. Mutually exclusive with `--sauver-verifier-reference` (rejected
at parse time, exit 2, if both are passed).

**Scope — what is compared:** `http_status`, `dom_stats`, and
`evaluations` (each `{"script", "valeur"}`). Volatile fields are excluded by
construction (timestamps, `operation_id`, `duree_ms`, `boussole.ip_locale`).

**`chemin_sensible_refuse` (`rpa.py`, exit 2):** `--checkpoint`,
`--sauver-verifier-reference`, or `--replay-verifier` was pointed at a `..`
traversal or a system-sensitive location (Dinoer's own install directories,
`/etc`, `/root`, `/boot`, `/sys`, `/proc`). Fix: pass a path under a
directory you control.

### Writing reference-safe assertions (v1.19.0)

The exclusion list only covers fields Dinoer itself produces. Anything your
own `evaluer` actions read from the target page is your responsibility: a
reference capture freezes `evaluations[]` values at reference time. A
legitimately dynamic value (visitor counter, live timestamp, session token
rendered in the DOM) produces a false `regression` on an actually healthy
page.

**Wrong (brittle) — asserts the exact value:**
```json
{"type": "evaluer", "script": "document.querySelector('.visitor-count').textContent"}
```

**Correct — assert the shape, not the value:**
```json
{"type": "evaluer", "script": "!isNaN(parseInt(document.querySelector('.visitor-count').textContent))"}
```

Apply this whenever building a reference for `monitor-verifier.sh` or
`--replay-verifier`: any field expected to change between runs by design
should be asserted as a shape — never as an exact value.

---

## Continuous structural monitoring — `scripts/monitor-verifier.sh` (v1.18.0)

Wraps the structural check into a single versioned command instead of an ad
hoc crontab line:

```bash
bash ~/git/Dinoer/Dinoer/scripts/monitor-verifier.sh \
  --scenario /opt/dinoer/scenarios/example_login.json \
  --reference /tmp/ref_sillage.json \
  --ntfy-topic dinoer-monitoring
```

**One pass per invocation — not a daemon.** Stable → silence (exit 0).
Regression detected → ntfy notification (exit 1, same as `rpa.py
--replay-verifier`). **Repetition is your job, by design** — cron or a
systemd timer, not the script.

**Fixed 16/08/2026 — `--no-capture`:** the script used to invoke
`rpa.py --no-capture --replay-verifier`, but `--no-capture` was no longer an
`rpa.py` flag — every real invocation was rejected by argparse. The dead
flag has been removed; Dinoer has no image-capture pathway by default, so
dropping it changes nothing else.

**First run — create the reference** (same as `--replay-verifier` above):
```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/example_login.json \
  --sauver-verifier-reference /opt/dinoer/references/example_login.ref.json
```

**Guide-read lock nuance:** if invoked under a distinct OS user (e.g. a
system service account), that user needs `--guide-version` validated once
(`~<home>/.config/dinoer/guide_state.json`) or `rpa.py` refuses with
`guide_non_lu`. The script never bypasses the lock.

---

## journal.py — operations log

`journal.py` and `lib/journal.py` append a structured JSON line to
`/var/log/dinoer/operations.jsonl` after each `shot.py`/`rpa.py` execution.
Logrotate handles `.1`, `.2.gz`, …

```bash
# Read the last 10 entries
tail -n 10 /var/log/dinoer/operations.jsonl | python3 -m json.tool --no-ensure-ascii
```

**Fields in each log entry** (corrected 15/08/2026 against `lib/journal.py`
directly, not assumed — see `docs/MANUEL.md` section 9 for the full,
current table): `ts`, `operation_id`, `outil` (`"shot.py"` or `"campagne.py"`
only — `rpa.py` never journals itself, it runs through `shot.py`'s dispatch;
corrected same day, `"rpa.py"` never appears here), `version`, `cible_url`, `resultat` (`"succes"` or
`"echec"`), `mutatif`, `source_scenario` (file name only, no path — lets
`dernier_diagnostic_host` identify a `diagnostic_dom.json` run without
parsing contents), `chainage` (list of `{scenario, profondeur, action_debut,
action_fin}`, present only when the scenario used `declencher_scenario`),
`intention`, `respect`, `evaluations` (sanitised `{script,
valeur_retournee}`), `erreur`. No `duree_ms` field exists — per-action
timing lives in a run's own JSON output (`latences_actions`), not in the
journal. Secrets and sensitive `evaluer` values are neutralised before
writing.

**When to read it:** after a failure in cron mode (no terminal output), to
audit intent/actions of a run, or to inspect the navigation ledger.

**Filtering flags (`journal.py` root CLI):** `--cible`, `--depuis`,
`--jusqu`, `--mutatif` (only writing runs), `--erreurs` (only entries where
the result was not success), `--intention`, `--format texte|json`, `--limite`,
`--exporter-skill OPERATION_ID --nom NOM`. Combine freely — all are AND-ed.

---

## Long-running operations — race-condition traps (FN7/FN8/FN9)

When an operation (batch job, file import, report generation) is triggered by
a click and takes several seconds to complete, do not use `pause` to wait.

**Wrong pattern (FN7):**
```json
[
  {"type": "cliquer", "selecteur": "button[data-testid='run-job']"},
  {"type": "pause", "ms": 10000}
]
```
`pause` does not adapt: if the operation takes 15 s you get a stale read; if
it takes 2 s you waste 8 s.

**Correct pattern — wait for a DOM signal:**
```json
[
  {"type": "cliquer", "selecteur": "button[data-testid='run-job']"},
  {"type": "attendre_absence", "selecteur": ".spinner"},
  {"type": "attendre_selecteur_present", "selecteur": ".result-container"},
  {"type": "evaluer", "script": "document.title", "contient": "Result"}
]
```

**FN7 exception:** when the app provides no DOM signal for completion — use
`pause` with manual re-reads via `evaluer`/`--a11y` to check state, then
proceed when the evidence you need is present.

**FN8 — delayed DOM element:** wait for visibility before acting:
```json
// WRONG — element may not be present yet
{"type": "pause", "ms": 3000},
{"type": "cliquer", "selecteur": ".lazy-button"}
// CORRECT
{"type": "attendre_selecteur_present", "selecteur": ".lazy-button"},
{"type": "cliquer", "selecteur": ".lazy-button"}
```

**FN9 — `attendre_absence` and the initial delay:** a POST redirect may not
have started when polling begins; the spinner may be a leftover from a
previous render. Use `delai_initial_ms` to let the new DOM state register:
```json
{"type": "attendre_absence", "selecteur": ".loading-overlay", "delai_initial_ms": 500}
```

---

## Cron mode notes

- Keep `DINOER_NTFY_URL` pointed at a private ntfy instance outside
  demonstration (the public `https://ntfy.sh` has no end-to-end encryption).
- **Never expose credential paths or values in cron commands.** Resolve
  credentials via the default encrypted directory or an explicitly scoped
  `--secrets` file — not a shell-visible environment.
- Each `monitor-verifier.sh` invocation is an isolated process — caps reset
  cleanly per run, no memory leak from a long-running daemon.

## Extraction recipe — open question beats narrow trove/valeur/url

Moved here from `GUIDE_LLM.md` (15/08/2026) to keep the index under its
250-line budget — content unchanged, only relocated.

`--extraire-cible "<demande>"` accepts any natural-language request — it is
not limited to a single fact lookup. On the reference campaign
(`spectacles-sud-finistere-2026-08-11-20`), a narrow question (trouve/valeur/url
for one specific fact) surfaced fewer, thinner results than an open question
that let the delegated model judge for itself whether it was reading a
one-off fact or a multi-day event (17/47 positive extractions, richer
content, vs. a narrower baseline — see
`_CADRE/SPECIFICATIONS/CARACTERISATION_DINOER.md` §7 for the full
comparison). Prefer an open, descriptive `<demande>` over a strict
fact-lookup phrasing when the source might describe a structured event
rather than a single fact.

For multiple positive extractions describing the same real event across
different pages, `lib/extraction.py::fusionner_evenements()` groups them —
call it on the filtered positive results before writing a final report,
rather than consolidating by hand. A single source can legitimately describe
several distinct events (an agenda page listing a concert, a workshop, a
guided tour on different dates) — the same source index is then cited in
each matching group, never treated as an error. Free-form reasoning before
the model's final JSON answer measurably improves grouping quality on this
task; forcing an immediate JSON-only answer produced short, under-reasoned
output on a real corpus (verified 13/08/2026).

## Synthesis relevance — two optional manifest fields, both reorder-only

The automatic report (`construire_contexte()`/`rediger_rapport()`, no
`--extraire-cible` involved) concatenates the collected corpus in file-write
order, truncated at 60000 chars — with no relevance ranking by default, the
most useful pages can fall outside that budget on a large corpus. Two
independent, optional manifest fields fix this, both reorder pages before
truncation, never exclude them outright:

- `"motifs_annee": ["2026"]`, `"motifs_mois": ["août", "aout", "/08", "-08-"]`
  — coarse pass, zero model call: pages that clearly don't mention the
  requested window are pushed to the end (include numeric date forms, not
  just the month name — some agenda widgets never spell it out).
- `"sujet_synthese": "<a sentence describing what the report is about>"` —
  fine pass, one grouped Ollama embedding call (`lib/vector.py::embed()`,
  a few seconds, nothing persisted to disk): pages are ranked by cosine
  similarity to this sentence. **Needed in addition to the coarse pass, not
  instead of it** — on the reference campaign, the coarse pass alone let a
  real event PDF pass as "probable" but still leave it ranked 27th of 29
  probable pages (still truncated out); the semantic pass alone correctly
  ranked it inside the budget. Measured, not assumed — see session 3 of
  `_CADRE/SPECIFICATIONS/PROCEDURES_LLM/TACHE_fiabilisation_synthese_campagne.md`.

Both default to absent — an existing manifest with neither field keeps the
exact pre-13/08/2026 behaviour.