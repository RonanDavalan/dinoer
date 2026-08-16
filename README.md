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

## Positioning: what Dinoer competes on, and what it doesn't

Dinoer does not compete with general-purpose search assistants (Perplexity
and similar) on discovery breadth, volume, or price. A real test (14 August
2026, reputation research on a real subject) measured this directly rather
than assuming it: on 28 pages collected by Dinoer's own SearXNG-driven
discovery, three sources a single unprepared Perplexity query surfaced
immediately (a LinkedIn profile, a project page, a stock-photo credit) were
entirely absent — traced to SearXNG queries aimed at the wrong kind of
search (company directories, not the terms that would have surfaced those
pages), not a ranking or truncation defect downstream. A generalist search
backend with authenticated, cookie-backed engines behind it has structural
reach that an unauthenticated local SearXNG instance does not.

What the same test did verify, on the same corpus, measured rather than
assumed: **a traceable, reproducible synthesis of a locked corpus.** Every
claim in a Dinoer report is attributable to a page actually collected to
disk (`collecte.jsonl`/`operations.jsonl`) — with zero dependency on
whatever a third-party search backend did while producing the answer. A
direct check of the delegated model's full event stream during synthesis
(not just its final text) confirmed zero external `websearch`/`webfetch`
calls reached the corpus during report generation. That is the actual
value proposition: know precisely where an answer came from, not find more
than a generalist tool would.

---

## Architecture

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

## Report quality: automatic draft vs. supervised research

`campagne.py`'s own end-of-run report (`lib/synthese.py::construire_contexte()`
builds and truncates the corpus, `rediger_rapport()` then drafts the text)
is a **working draft**, not the polished deliverable: it concatenates the
collected corpus in file order, truncated at 4000 characters/page and 60,000
total — no relevance ranking. On a large, noisy corpus this reliably admits
generic or off-topic pages ahead of the actual sources, and can silently drop
the most relevant ones past the truncation point.

On one real research task (a local events listing, see "Positioning" above
for a task where the result went the other way), the report quality
demonstrably outperformed a general-purpose search tool (Perplexity) — but
that report was **not** produced by a single `campagne.py` run. It came
from an operator looping `campagne.py --extraire-cible` — dozens of
individual, open-ended extraction calls against the same collected corpus,
each one letting the delegated model judge for itself whether it was
reading a one-off fact or a multi-day event — followed by manual
consolidation of the results. See [`docs/GUIDE_LLM.md`](docs/GUIDE_LLM.md)
for the exact extraction pattern.

If you need a quick, non-critical summary, the automatic report is fine as a
starting point. If you need a report you can trust unsupervised, use the
targeted, looped extraction pattern instead.

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

Two channels, mutually exclusive on one machine.

**`.deb` package** — the normal path if you want to use Dinoer as-is:

```bash
sudo apt install ./dinoer_1.0.0-1_all.deb
```

Installs the `dinoer` system user and group, an isolated Python virtual
environment, Chromium, the six `dinoer-*` commands and their manual pages in
four languages. Package, sources and checksums are published on
[dinoer.davalan.fr](https://dinoer.davalan.fr) — see the
[Downloads](https://dinoer.davalan.fr/en/guides/downloads/) page for details,
including what that `apt` sandbox notice means.

**Git clone** — if you intend to modify the code:

```bash
git clone https://github.com/RonanDavalan/dinoer.git
cd dinoer
bash scripts/install.sh
```

This creates the `dinoer` system user and group, the virtual environment,
deploys the code to `/opt/dinoer/`, and runs a smoke test
(`shot.py --a11y` against a real URL).

Configuration lives in `/etc/dinoer/dinoer.conf` (`.deb` channel) or
`/opt/dinoer/dinoer.conf` (git-clone channel); a sample is installed next to
it as `dinoer-sample.conf` — plain JSON, not commented (corrected 15/08/2026:
JSON has no comment syntax, the file never was). Exception: `campagne.py`
never reads `DINOER_CONF` or the git-clone path above — it reads
`/opt/dinoer/dinoer.conf` hardcoded and resolves its own paths via dedicated
env vars (`DINOER_CAMPAGNES_DIR`, `DINOER_SEARXNG_URL`,
`DINOER_TABLES_REFERENCE`, `DINOER_JOURNAL`).

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
~/Vaults/__PROJET__/Dinoer/
├── my-source.example.json   → {"password": "...", "username": "admin"}
└── other-service.com.json   → {"password": "...", "api_key": "..."}
```

In a scenario or action: `"valeur": "depuis_secrets", "secret_cle":
"password"` — Dinoer reads the credential at runtime from the credentials
directory.

The path is configurable via `/opt/dinoer/dinoer.conf` or the
`DINOER_SECRETS_DIR` environment variable.

**Recommendation:** protect `~/Vaults/__PROJET__/Dinoer/` with `chmod 700` and encrypt
it with `gocryptfs` (see `scripts/configurer-repertoire-chiffre.sh
--gocryptfs` — git-clone channel only, not shipped by the `.deb`; on that
channel, set up `gocryptfs` yourself and point `secrets_dir` at the mounted
path). If the encrypted directory is initialised but not mounted, Dinoer
returns a structured `SecretsFermesError` (exit code 42) instead of
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
`~/Vaults/__PROJET__/Dinoer/` — contains credentials in plaintext JSON when unmounted.
Protect it:

```bash
chmod 700 ~/Vaults/__PROJET__/Dinoer/
```

See `~/git/Dinoer/Dinoer/SECURITY.md` for the vulnerability disclosure
policy.

---

## Documentation in other languages

This is the English source. [`docs/fr/README.md`](docs/fr/README.md),
[`docs/de/README.md`](docs/de/README.md) and
[`docs/es/README.md`](docs/es/README.md) are translations derived from it
(resynchronised 15/08/2026), together with `docs/MANUEL.md`, `docs/GUIDE.md`,
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
`lib/searxng.py`, `lib/fetch_leger.py`, `lib/selection_candidats.py`,
`lib/extraction.py`, `lib/tables_reference.py`, `lib/cache_recherche.py`),
removal of the perception layer. Principal author of the source code.

**Synthesizer & Strategic Advisor:** Gemini (Google)
Independent architectural analysis, logical conflict resolution, workflow
optimisation, cross-validation of technical decisions.

---

## Licence

MIT — see `LICENSE` file.
