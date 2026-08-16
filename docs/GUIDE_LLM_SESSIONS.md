# Dinoer — Sessions guide (encrypted directory, credentials, SPA, MFA, multi-page)

<!-- notice-version: 1.3 -->
Version 1.3 — August 2026. This number counts revisions of this notice, not
releases of Dinoer. Notable in the current text: full rewrite for the public
repo — the previous vision/numbering surface was removed; credential fields
are `remplir` + `secret_cle` (not numbered elements); `attendre_mfa_ntfy`
takes a `selecteur`; config is `dinoer.conf` with key `secrets_dir`; ntfy URL
from `DINOER_NTFY_URL`. Prior (v1.0/v1.1): `action_secret_en_clair` and
`url_scheme_interdit` error codes; `dernier_code_http` in boussole;
`--http-credentials` confirmed against a real Caddy target.

Load this notice when: credentials, `--secrets`, session persistence, SPA
navigation, multi-page flows, MFA/TOTP, auth_indicator, `--http-credentials`,
`--ignore-tls-errors`.

---

## Security rules — non-negotiable

**FORBIDDEN — extracts credential into shell:**
```bash
PASS=$(jq -r '.password' ~/Vaults/.../file.json)   # NEVER
USER=$(jq -r '.username' ~/Vaults/.../file.json)    # NEVER
```

**CORRECT — credentials resolved inside Playwright by lib/repertoire_chiffre.py:**
```json
{"type": "remplir", "selecteur": "input[name=\"username\"]", "valeur": "depuis_secrets", "secret_cle": "username"}
{"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"}
```

Values never appear in shell, bash history, process list, or any log.
Also forbidden: using `curl`, `wget`, or any HTTP client for authentication.

**`action_secret_en_clair` (`rpa.py`, exit 1):** a scenario action carries a
plaintext value on a `password`/`secret`-looking selector or field instead of
`"valeur": "depuis_secrets"` + `"secret_cle": "..."`. Checked before the
scenario ever reaches Playwright's argv. Fix: replace the plaintext value
with the `depuis_secrets` form above — this is the only accepted shape,
scenario JSON or not, test tenant or not.

**`url_scheme_interdit` (`shot.py`/`rpa.py`, exit 2):** the target URL —
`--url`, a scenario's `url` field, or the URL restored by
`--reprendre-session` — uses a scheme other than `http`/`https` (e.g.
`file://`, `javascript:`), or carries userinfo (`user:pass@host`). Fix:
pass a plain `http(s)://host/path` URL; resolve credentials through
`depuis_secrets`, never through the URL itself.

---

## Credentials — how it works

Credentials live in a JSON file inside an encrypted directory (a gocryptfs
volume, mounted by the operator). `lib/repertoire_chiffre.py` reads the
mounted file; it never exposes values in the shell.

The encrypted directory is configured by `secrets_dir`, read from a JSON
conf file. Corrected 15/08/2026 — not a three-step fallback: `DINOER_CONF`
(if set) names that file directly, whatever its path — `~/.dinoer.conf` is
only a naming convention for where operators commonly point it, never an
automatic second step. Unset, it defaults to `/opt/dinoer/dinoer.conf`
(`lib/repertoire_chiffre.py::_chemin_secrets`).
You never need to know the exact path — pass `--secrets` when you need a
specific file, otherwise the default directory is used.

`secret_cle` is the JSON key inside the decrypted file (e.g. `"username"`,
`"password"`, `"totp_cle"`, `"ntfy_topic"`).

**If the encrypted directory is closed** (gocryptfs not mounted): shot.py
exits with `SecretsFermesError`, exit code 42. Don't try to mount it
yourself — ask the operator to run `scripts/monter-repertoire-chiffre.sh`.
If no encrypted directory is configured at all: `SecretsNonConfigureError`,
exit code 43.

**Your responsibility — writing new credential files:** Dinoer's own
journal/proof writes detect a closed directory before writing. If *you*
construct or update a credential file yourself (shell command, `evaluer`
outside the `depuis_secrets` mechanism), the same risk is not automatically
caught: an unmounted directory exists on disk but is empty and unencrypted.
Before creating or updating a credential file, confirm it is mounted — the
directory must be non-empty. If in doubt, stop and ask the operator to
verify — never write credentials assuming it is open.

---

## `--secrets` — specifying a non-default credentials file

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ \
  --actions /opt/dinoer/scenarios/my-scenario.json \
  --secrets ~/Vaults/Dinoer/other-project/creds.json
```

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/my-scenario.json \
  --secrets ~/Vaults/Dinoer/other-project/creds.json
```

**`origines_autorisees` — mandatory (breaking change, no compatibility
period):** every `--secrets` file must declare which hostnames it may be used
against, or it is refused before any read:

```json
{"username": "u", "password": "p", "origines_autorisees": ["target.local"]}
```

Without `--secrets`, a credential is bound to the domain actually loaded in
the browser (`domaine_depuis_url(page.url)`) — a redirection to another
domain fails resolution. `--secrets` reads a designated file regardless of
that origin unless `origines_autorisees` is present; a domain outside the
list refuses the read (`SecretsOrigineNonAutoriseeError`), same exit family
as a closed encrypted directory (42).

**`--secrets` is a single value, not repeatable:** a second occurrence
silently overrides the first, it does not accumulate. "Multiple files" means
across runs: each run picks the right file explicitly via `--secrets`, instead
of relying on automatic per-hostname resolution. **The filename is whatever
the operator chose — never assume it matches the target's hostname** (e.g. a
file named `client-a.json` can hold credentials for `app.client-a.example`);
`ls` the credentials directory or ask rather than guess.

---

## Mode A (interactive — shot.py direct)

Use Mode A for exploration and navigation-state reads with a loop:

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/ \
  --a11y
```

Output: JSON with `a11y_tree`, `dom_stats`, `boussole`, plus `evaluations`,
`extraction_texte` and the action-state fields. You read the text tree,
decide the next selector, and pass it in the next `--actions` call.

**Keep Mode A alive across steps:** pass `--actions` with accumulated actions
each time. Closing and reopening shot.py loses the browser session. Use
`--sauver-session` to save the session state to a JSON file, then
`--reprendre-session` to reload it on the next call.

---

## Mode B (RPA — rpa.py declarative)

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/scenarios/login-check.json
```

rpa.py collects all `evaluations[]` and runs the `attendu`/`contient`/`motif`
assertions. **stdout is a single JSON line** — pipe freely.

**When to choose Mode B over Mode A:**
- The flow is already known and validated in Mode A
- The task must run unattended (cron, scheduled check)
- You are building a test suite

---

## Session persistence across calls (`--reprendre-session`)

```bash
# First call — authenticate and save session
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/login \
  --actions login_actions.json \
  --sauver-session /tmp/dinoer/session.json

# Subsequent calls — reuse session
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/dashboard \
  --reprendre-session /tmp/dinoer/session.json
```

**Note:** `shot.py` no longer deletes the session file at end of run.
`--reprendre-session` without `--sauver-session` is safe across chained
calls. Add `--sauver-session` only to refresh the on-disk session state.

**Warning — session drift signal:** if the session has expired or the app
redirected you to the login page, `boussole.session_derive` appears in the
JSON output. Corrected 15/08/2026, verified against `shot.py:1530-1537`: it
is an **object** (`{url_sauvegardee, url_reprise, ...}`), never the boolean
`true` — presence of the key is the signal, not its value. Check it after
every `--reprendre-session` call.

```json
"boussole": {
  "session_derive": {
    "url_sauvegardee": "https://target.local/dashboard",
    "url_reprise": "https://target.local/login"
  },
  "url_courante": "https://target.local/login",
  "dernier_code_http": 302
}
```

If `session_derive` is present: run the full login flow again without
`--reprendre-session`.

**`dernier_code_http`, always present, disambiguates the cause:** a real
expired session and a masked server-side error (e.g. `display_errors=0`
hiding a 500) both redirect to the same login page — `session_derive` looks
identical either way. Compare `dernier_code_http`: `302`/`200` on the
redirect points to a real session expiry, `500`/`4xx` points to an
application error, not your session. **Nuance:** on a run with several
navigations, it reflects the *last* one only — not necessarily the one that
explains the drift.

---

## Checkpoints for long scenarios (`rpa.py --checkpoint`, v1.17.0)

A checkpoint is **session state + action-list position** — never a DOM
snapshot. Open modals, half-filled fields, unsubmitted forms are never
preserved between two invocations (same constraint as `--reprendre-session`).
Only a boundary between two fully-completed actions is a valid resume point.

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario long_scenario.json --checkpoint /tmp/mon_run.checkpoint.json
```

- First run: executes from action 0. On mid-scenario failure, writes the
  checkpoint with `{"actions_completees": N, "session_file": ...}` and
  preserves the browser session as of the failure point.
- **Relaunch the exact same command** to resume: already-completed actions
  are skipped, the run continues from the saved session's URL.
- On full success: the checkpoint file is deleted automatically.
- On failure with no recoverable progress (e.g. encrypted directory closed
  before any action ran): the checkpoint file is left untouched.
- **Navigation cap reached:** if the run stops because
  `max_actions_par_run`/`max_pages_par_run` was hit, it returns `succes: true`
  like a genuinely completed section and the checkpoint is *updated* with the
  actual progress — relaunch the same command to continue. (v1.17.2 fixed a
  bug that deleted it in this case, silently losing remaining progress.)

**Not a substitute** for `--sauver-session`/`--reprendre-session` used
directly — checkpoints are for long, single-scenario runs where a late
failure would otherwise mean replaying everything from action 0.

---

## SPA navigation — rules

Single-page applications (React, Vue, Angular) do not reload the page on
navigation. Playwright's default navigation wait (`load` event) never fires.

**Rules:**
1. After clicking a navigation link → add `attendre_url` or `attendre_selecteur_present`
2. After a form submission → add `attendre_url` or `attendre_selecteur_present`
3. Never assume navigation is complete after a click alone

```json
[
  {"type": "cliquer", "selecteur": "a[href*='/dashboard']"},
  {"type": "attendre_url", "motif": "dashboard"},
  {"type": "evaluer", "script": "document.title", "contient": "Dashboard"}
]
```

Note: `motif` in `attendre_url` is a URL glob substring (not a Python regex),
and matches partially — pair it with `attendre_selecteur_present` or
`"attendre_changement": true` after a submit (see INTERACTIONS, pitfall
FR-55). `motif` in `evaluer` is a Python `re.search()` expression.

---

## Multi-page flows and subdomain navigation

When a flow crosses domains or requires a full page reload:

```json
[
  {"type": "cliquer", "selecteur": "a[href*='/admin']"},
  {"type": "attendre_navigation"},
  {"type": "evaluer", "script": "window.location.href", "contient": "/admin"}
]
```

After `attendre_navigation` the browser has loaded the new page; a new read
(`--a11y`, `evaluer`) reflects the new document.

---

## `attendre_reseau_calme` — wait for AJAX to finish

```json
[
  {"type": "cliquer", "selecteur": "button[type=submit]"},
  {"type": "attendre_reseau_calme", "timeout_ms": 10000},
  {"type": "evaluer", "script": "document.querySelector('.saved')?.textContent ?? null", "contient": "ok"}
]
```

Internal silence threshold: 500 ms of network inactivity. `timeout_ms` is the
maximum total wait before abort (distinct from the silence threshold).

---

## `auth_indicator` — authentication status (v1.9.0)

Declare a CSS selector that is only visible when the user is authenticated;
shot.py checks for it on every capture.

```json
{
  "url": "https://target.local/",
  "auth_indicator": ".user-avatar",
  "actions": [...]
}
```

Output includes `auth_status: "active"` when the selector is found,
`"inactive"` otherwise. If `auth_indicator` is not set: `auth_status` is
absent from the output.

**`auth_indicator_negative` — disambiguation (v1.14.0):** on some interfaces
the positive selector (e.g. `.user-menu`) is visible even on the login page.
Cross-check with a negative selector:

```json
{"auth_indicator": ".user-menu", "auth_indicator_negative": ".btn-login"}
```

Logic: `auth_status = "active"` if positive selector visible **AND** negative
selector absent or not visible. `--auth-indicator-negative` exists on the CLI
(indirect flavor: `--auth-indicator` required first — both are rechecked for
compatibility when flags are involved).

---

## Reading pages — `--a11y` semantics

Dinoer has no image-capture pathway: reading a page means `--a11y`
(accessibility snapshot) and/or `--actions` running `evaluer`/`extraire_texte`.
Text-only reads are the default, not an explicit option.

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://target.local/api/status --a11y
```

`a11y_tree` and `evaluations` are conditional (corrected 15/08/2026, verified
against `shot.py:1509-1516`): `a11y_tree` only with `--a11y`, `evaluations`
only when at least one `evaluer` action ran. The `boussole` describes the
state honestly (including `a11y_redaction_echouee` if the tree could not be
built).

---

## MFA / TOTP flows

`attendre_mfa_ntfy` waits for a TOTP code pushed via the ntfy notification
system. Requires the ntfy integration to be configured.

```json
[
  {"type": "cliquer", "selecteur": "button[type=submit]"},
  {"type": "attendre_mfa_ntfy", "selecteur": "input[name=otp]", "timeout": 120}
]
```

`selecteur`: the CSS selector of the OTP input field (there is no element
numbering in Dinoer). `timeout`: max wait in seconds (default 120). The
action polls the ntfy topic for a 4-to-8-digit code (non-matching messages
are ignored), then fills the input field. It does **not** read the
credentials file — the code is pushed live by the authenticator.

`secrets_cle` `ntfy_topic` names the topic to subscribe to (same resolved
file as the run's credentials). The ntfy base URL comes from
`DINOER_NTFY_URL` (env) or the `ntfy.url` key of `dinoer.conf`.

**Production deployments:** the default `https://ntfy.sh` is a public
service with no end-to-end encryption. Point `DINOER_NTFY_URL` at a private
ntfy instance outside demonstration use.

**Manual TOTP fallback** (no ntfy):
```json
[
  {"type": "remplir", "selecteur": "input[name=otp]", "valeur": "depuis_secrets_totp"},
  {"type": "cliquer", "selecteur": "button[type=submit]"}
]
```

`"depuis_secrets_totp"` resolves `totp_cle` (base32 seed) and computes the
live code inside Playwright — never type a TOTP into a scenario. Requires
human intervention only if you deliberately hardcode a fixed code for a test
tenant (prefer the TOTP form above).

---

## Skills — calling a named sub-sequence

Reusable action sequences defined in `skills/` (JSON files, same schema as
`scenarios/*.json` — see `skills/README.md`). Corrected 15/08/2026: not
invoked via `declencher_scenario`, which resolves with `confiner=True`
(`rpa.py::resoudre_chemin_scenario`) and only ever accepts a path that
resolves inside `scenarios/` — `skills/` is unreachable from it. Run a
skill directly instead:

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/skills/login_myapp.json
```

**Common pattern:** define the authentication sequence as a skill, run it
standalone at the start of a session, then reuse the saved session
(`--sauver-session` / `--reprendre-session`) for scenarios that need a
logged-in state — `declencher_scenario` cannot inline a skill from outside
`scenarios/`.

---

## Session summary — checklist

| Task | Action |
|---|---|
| First login | Mode A with `--actions`, then check `auth_status` |
| Persistent session | Add `--reprendre-session` to next calls |
| Session drift detected | Re-run login without `--reprendre-session` |
| SPA navigation | Always add `attendre_url` + selector wait after click |
| Credential fill | `valeur: "depuis_secrets"` + `secret_cle` — never shell |
| Non-default credentials file | `--secrets /path/to/creds.json` (with `origines_autorisees`) |
| OTP in real-time | `attendre_mfa_ntfy` or `depuis_secrets_totp` |

---

## `--ignore-tls-errors` — LAN and internal PKI targets (v1.15.1)

By default, Playwright rejects invalid TLS certificates. This is the secure
default.

On internal networks using a self-signed CA (Step-CA, mkcert, corporate PKI)
or a LAN device with a self-signed certificate:

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://router.local/ \
  --ignore-tls-errors
```

Or via rpa.py (propagated automatically). When active,
`boussole.tls_errors_ignored: true` appears in the JSON output.

**Never use on public internet targets.** An invalid TLS certificate on a
public target is a strong signal of a TLS interception attack (MITM). Do not
pass this flag unless you have a specific, documented reason for a controlled
LAN or dev environment.

---

## `--http-credentials` — HTTP Basic Auth (v1.21.0)

Dinoer's credential resolution handles web **form** authentication (`remplir`
+ `depuis_secrets`). It does not, on its own, answer a browser-level HTTP
Basic Auth challenge (RFC 7617) — the kind a reverse proxy (Caddy, nginx,
Traefik) raises before any page renders. `--http-credentials` closes that gap.
It does **not** mean form-based authentication is unsupported — the two are
unrelated mechanisms (non-presumption rule, `docs/GUIDE_LLM.md`).

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
  --url https://internal.example/ \
  --http-credentials
```

Or via `rpa.py` (propagated automatically), or as a scenario root property
`"http_credentials": true` — combinable with the CLI flag (boolean, OR).

**Credential keys:** `http_username`/`http_password` tried first (needed only
if the same target also has a separate application-level login behind the
Basic Auth wall — two different credential pairs in the same file). If
absent, falls back to the plain `username`/`password` keys — the common case,
confirmed against a real Caddy-protected target: most credentials files
already have exactly this pair for a single-credential target. Resolved from
the same file already in scope for the run (`--secrets` if passed, otherwise
the default file by hostname). Never passed on the command line.

**Security — non-negotiable:** identifiers are scoped to the target's origin
(`scheme://host:port`) and sent only after a real 401 (`send:
"unauthorized"`). This is not configurable per-run — it protects against
Dinoer sending credentials to a third-party origin (CDN, tracker, redirect)
loaded inside the same browser context.

**When it may still fail:** if a target never issues a clean 401 (some
reverse proxies expect credentials preemptively), `--http-credentials` will
not resolve the challenge — a known limit of the safe default.
`boussole.http_auth_requise: true` confirms a 401 was actually hit;
`boussole.http_credentials_actif: true` confirms the challenge was actually
resolved (never just that the flag was passed — same discipline as
`stealth_actif`).

---

## Pre-condition pattern — securing scenario entry

Before any **mutating action** (delete, submit, write), add an `evaluer`
assertion as the first action to verify you are on the expected page. Guards
against orphaned actions when a session expired in the background or a
redirect landed on the wrong page.

```json
{"type": "evaluer", "script": "window.location.href", "contient": "/dashboard"}
```

```json
{"type": "evaluer", "script": "document.title", "contient": "Dashboard"}
```

```json
{"type": "evaluer", "script": "document.querySelector('.alert-danger')?.textContent ?? null", "attendu": null}
```

```json
{"type": "attendre_selecteur_present", "selecteur": ".user-logged-in"}
```

**Fail-fast behaviour:** if the assertion fails, `rpa.py` exits immediately
(exit 1) with a structured diagnostic before any mutating action runs. Place
the guard as action index 0 in any scenario that performs deletions or
sensitive writes.