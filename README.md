# Dinoer — Sovereign, Local-First Web Research for LLM Agents

> **For the human operator:** Dinoer runs on your own machine, delegates search
> and collection to primitives you can read line by line, and hands you a
> sourced, dated Markdown report — not a black-box answer.
>
> **For the LLM:** [`docs/GUIDE_LLM.md`](docs/GUIDE_LLM.md) is your operational
> reference. Start there.

---

## What is Dinoer?

Dinoer is a **passive, local-first, sovereign search and synthesis engine**.
It is a fork of [Diwall](https://github.com/RonanDavalan/diwall) (visual
browser automation for LLMs), stripped of its entire perception layer —
**zero screenshots, zero Set-of-Mark, zero vision model.** Dinoer never looks
at a page; it reads it: DOM, accessibility tree, and cleaned page text.

Where Diwall answers "interact with one authenticated interface, visually,"
Dinoer answers a different question: "explore a large number of public
sources and compile a sourced, verifiable signal from them" — on hardware as
modest as a Raspberry Pi 5.

```
Query → SearXNG discovery → lightweight HTTP collection
      → escalation to a real browser only for pages that need it
      → synthesis by a delegated LLM → dated, sourced Markdown report
```

**Doctrine:** the Python code carries no business intelligence. Each module
does one mechanical thing — query SearXNG, extract clean text from a page,
read an encrypted credential, send a notification. The *strategy* of a
search (how to follow up, when to escalate, when to stop) lives in a
scenario, never hard-coded in a module. See
[`docs/GUIDE_LLM.md`](docs/GUIDE_LLM.md) for the full doctrine.

---

## Architecture

```
campagne.py (orchestration)
  ├─ lib/searxng.py         → SearXNG JSON API (HTTP only, no browser)
  ├─ lib/fetch_leger.py     → requests + BeautifulSoup, robots.txt-aware
  ├─ rpa.py / shot.py       → Playwright, only for pages the light tier
  │                           marked "insufficient" (JS-only shells)
  ├─ lib/extraction.py      → targeted fact extraction, trouve/valeur/url
  ├─ lib/tables_reference.py→ persistent, sourced table of reference sites
  ├─ lib/cache_recherche.py → ChromaDB-backed search cache
  └─ lib/synthese.py + lib/modeles.py → delegated LLM (OpenCode/Ollama),
                                        writes the final report
```

`shot.py`/`rpa.py` retain Diwall's ReAct execution core (`naviguer`,
`remplir`, `cliquer`, `evaluer`, session persistence, credential
resolution) — none of its perception layer.

---

## Capabilities

| Feature | Description |
|---|---|
| **SearXNG discovery** | Pure HTTP query against a local or remote SearXNG instance — no browser cost paid for search |
| **Light-tier collection** | `requests` + BeautifulSoup extraction, `robots.txt`-aware, WAF-aware |
| **Heavy-tier escalation** | Playwright, used only for pages the light tier could not read (JS-rendered shells) |
| **Semantic text extraction** | `extraire_texte` action — cleaned main-content text, not a screenshot |
| **Accessibility snapshot** | `--a11y` — semantic page structure (A11y tree), no image ever produced |
| **Targeted extraction** | `lib/extraction.py` — strict `trouve`/`valeur`/`url` contract, declares absence rather than inventing an answer |
| **Reference-site tables** | `lib/tables_reference.py` — a persistent, sourced table of known sites per topic |
| **Vector search cache** | `lib/cache_recherche.py` — ChromaDB-backed, avoids re-querying for near-duplicate requests |
| **Deduplication & freshness** | Campaign-level dedup by exact URL, per-hostname cap, 30-day freshness window before re-crawl |
| **Respectful crawling** | Random delay between targets, hard refusal on WAF/robots.txt signals — never bypassed |
| **Credential resolution** | Secure credential injection — never in plaintext, never on the command line |
| **Encrypted directory** | gocryptfs volume — `SecretsFermesError` (exit 42) if it is not mounted |
| **Operation log** | Persistent append-only log of all runs — who did what, where, when |
| **RPA scenarios** | Execute action sequences from JSON files, for the heavy-tier escalation path |
| **Cross-origin iframes** | `cliquer_iframe` / `remplir_iframe` target elements inside iframes |
| **TOTP / async MFA** | Credential-gated targets can still be reached when a heavy-tier run needs to authenticate |

---

## Requirements

| Component | Version / Notes |
|---|---|
| **OS** | Debian 13 Trixie (Linux) |
| **Python** | 3.11+ in isolated venv (PEP 668 — system pip blocked on Debian 13) |
| **Playwright** | 1.62+ (installed in venv) — used only by the heavy-tier escalation path |
| **Chromium** | Headless, installed via `playwright install chromium` |
| **SearXNG** | A reachable instance (local or remote), HTTP JSON API |
| **Ollama** | Local, CPU-friendly embedding model (`nomic-embed-text`) for the search cache — no vision model, no GPU required |
| **OpenCode** | Delegated reasoning back-end for report synthesis (free-tier models by default) |

No GPU is required. The reference target is a Raspberry Pi 5, 8 GB RAM.

---

## Installation

Git-clone channel only. **A `.deb` package is not offered yet** — packaging
is deliberately deferred until the product stabilises.

```bash
git clone https://github.com/RonanDavalan/dinoer.git
cd dinoer
bash scripts/install.sh
```

This creates the `dinoer` system user and group, the virtual environment,
deploys the code to `/opt/dinoer/`, and runs a smoke test
(`shot.py --a11y` against a real URL).

Configuration lives in `/etc/dinoer/dinoer.conf` (or `/opt/dinoer/dinoer.conf`
depending on your `deploy.sh` target); a commented sample is installed next
to it as `dinoer-sample.conf`.

### Uninstallation

```bash
bash scripts/uninstall.sh --dry-run   # preview, no changes made
bash scripts/uninstall.sh             # interactive confirmation
```

Removes: `/opt/dinoer/`, `/var/log/dinoer/`, system user `dinoer`, system
group `dinoer`. **Never touched:** `~/Vaults/` (your credentials), the
repository itself.

---

## Usage (by your LLM)

### Semantic extraction, no image

```bash
/opt/dinoer/venv/bin/python3 /opt/dinoer/shot.py \
  --url https://example.com --a11y --action '{"type":"extraire_texte"}'
```

### A research campaign

```bash
python3 /opt/dinoer/campagne.py --manifeste manifeste.json
```

Full LLM reference: [`docs/GUIDE_LLM.md`](docs/GUIDE_LLM.md)

---

## Credentials

Credentials are stored in JSON files, one per domain, **never in code or
scenario files**:

```
~/Vaults/Dinoer/
├── my-source.example.json   → {"password": "...", "username": "admin"}
└── other-service.com.json   → {"password": "...", "api_key": "..."}
```

In a scenario or action: `"valeur": "depuis_secrets", "secret_cle":
"password"` — Dinoer reads the credential at runtime from the credentials
directory.

The path is configurable via `/opt/dinoer/dinoer.conf` or the
`DINOER_SECRETS_DIR` environment variable.

**Recommendation:** protect `~/Vaults/Dinoer/` with `chmod 700` and encrypt
it with `gocryptfs` (see `scripts/configurer-repertoire-chiffre.sh
--gocryptfs`). If the encrypted directory is initialised but not mounted,
Dinoer returns a structured `SecretsFermesError` (exit code 42) instead of
silently failing.

---

## Security

### Local vs cloud models

Report synthesis is delegated to OpenCode or a local Ollama model. Collected
page text may transit to whichever back-end you configure — review
`lib/modeles.py` before pointing Dinoer at a cloud provider on sensitive
sources.

### Credentials directory

The credentials directory — wherever you pointed `secrets_dir`, for example
`~/Vaults/Dinoer/` — contains credentials in plaintext JSON when unmounted.
Protect it:

```bash
chmod 700 ~/Vaults/Dinoer/
```

See `~/git/Dinoer/Dinoer/SECURITY.md` for the vulnerability disclosure
policy.

---

## Documentation in other languages

This is the English source. [`docs/fr/README.md`](docs/fr/README.md),
[`docs/de/README.md`](docs/de/README.md) and
[`docs/es/README.md`](docs/es/README.md) are translations derived from it
(resynchronised 12/08/2026), together with `docs/MANUEL.md`, `docs/GUIDE.md`,
`docs/CHEAT_SHEET.md` and the `dinoer.1` man page in each language.
`docs/GUIDE_LLM.md` and its three notices exist in English only and are
never translated — locked path, guide-lock mechanism.

---

## For LLMs discovering Dinoer

If you are a language model reading this README: see
[`docs/GUIDE_LLM.md`](docs/GUIDE_LLM.md) for the complete technical
reference — invocation patterns, credential integration, and the research
pipeline (`campagne.py`).

---

## Credits

This project was developed using an **asymmetric human-LLM collaboration
model**. Roles are documented formally to reflect the actual work performed.

**Architect & Arbiter:** Ronan Davalan
Product vision, security requirements, project direction, validation and
testing. All architectural decisions are validated by him.

**Systems Engineer & Lead Developer:** Claude Code (Anthropic)
Fork of Diwall's ReAct core, the research pipeline (`campagne.py` and
`lib/searxng.py`, `lib/fetch_leger.py`, `lib/extraction.py`,
`lib/tables_reference.py`, `lib/cache_recherche.py`), removal of the
perception layer. Principal author of the source code.

**Synthesizer & Strategic Advisor:** Gemini (Google)
Independent architectural analysis, logical conflict resolution, workflow
optimisation, cross-validation of technical decisions.

---

## Licence

MIT — see `LICENSE` file.
