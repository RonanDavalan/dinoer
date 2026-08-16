% DINOER(1) | Dinoer commands
%
% August 2026

# NAME

dinoer - ReAct-based web automation and research toolkit for LLM agents

# SYNOPSIS

**shot.py** \[*options*\] **--url** *URL*

**rpa.py** \[*options*\] **--scenario** *FILE*

**campagne.py** \[*options*\] **--manifeste** *FILE*

**journal.py** \[*options*\]

**scripts/monter-repertoire-chiffre.sh**

**scripts/demonter-repertoire-chiffre.sh**

**scripts/monitor-verifier.sh** **--scenario** *FILE* **--reference** *FILE*

# DESCRIPTION

Dinoer gives an LLM agent hands on web interfaces it cannot otherwise
operate: Playwright-driven actions driven by a ReAct execution core, with
an accessibility tree (`--a11y`) as the eyes when the agent reads state.
Every command prints a single JSON object on standard output, designed to
be read by a program rather than by a human.

Dinoer ships two ways: this `.deb` package, or a git clone installed by
**scripts/install.sh** under **/opt/dinoer/** for whoever intends to modify
the code. The Python entry points run through the virtual environment:

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py ...

For the exhaustive option list of any command, run it with **--help** —
that output is always authoritative over this page.

# COMMANDS

**shot.py**
: Captures a page and returns JSON describing it. With **--a11y**, the
accessibility tree is included. Actions can be executed in the same browser
session via **--actions** (a JSON file). **--reprendre-session** reuses
cookies only, never DOM state.

**rpa.py**
: Executes a scenario file (JSON) describing a sequence of actions, and
returns one JSON line. This is the command to use for anything repeatable,
and the only one that evaluates scenario assertions and supports
**--replay-verifier**.

**campagne.py**
: Orchestrates a deep-research campaign from a JSON manifest: per-source
pagination, vector-cache de-duplication, targeted extraction without
synthesis. Reads its configuration from **dinoer.conf**.

**journal.py**
: Reads the append-only operation log at **/var/log/dinoer/operations.jsonl**.
Filters by target, date, mutability, errors or intention; outputs plain
text or JSON.

**scripts/monter-repertoire-chiffre.sh**, **scripts/demonter-repertoire-chiffre.sh**
: Mount and unmount the gocryptfs-encrypted credentials directory. Dinoer refuses
to resolve any credential while it is closed, exiting with status 42
rather than falling back to anything weaker. Configured once by
**scripts/configurer-repertoire-chiffre.sh**.

**scripts/monitor-verifier.sh**
: Runs one structural non-regression pass of a scenario against a saved
reference and exits non-zero on divergence. Intended to be driven by cron or
a systemd timer; it contains no loop of its own.

# COMMON OPTIONS

The options below are shared by **shot.py** and **rpa.py** unless stated
otherwise. This is a selection, not the full list.

**--guide-version** *X.Y*
: Mandatory proof that **/opt/dinoer/docs/GUIDE_LLM.md** was read. Without it
— and without a still-valid local marker — the command refuses to run and
exits 1. The expected value is the *notice-version* comment on line 3 of that
guide. This is the one place where Dinoer is not opt-in.

**--version**
: Print the installed version as JSON and exit, without starting a browser.
Distinct from **--guide-version**; the two numbers are unrelated.

**--a11y**
: Include the accessibility tree in the JSON output. The agent reads the DOM
through this tree; Dinoer has no screenshot or image-capture pathway.

**--wait-until** *networkidle*|*load*|*domcontentloaded*
: When the initial navigation is considered finished. The default,
*networkidle*, waits for 500 ms of network silence and is right for most
targets. A page that polls continuously never goes silent — use *load* there;
raising **--timeout** cannot help, since the page will never finish.

**--timeout** *MS*
: Per-operation timeout in milliseconds (default 10000).

**--stealth**
: Remove the automatic markers that identify a headless browser. It does not
change the operator's IP address and does not forge an identity — the point
is equal treatment, not disguise.

**--secrets** *FILE*
: Resolve credentials from an explicit JSON file inside a mounted directory,
instead of the default host-based lookup. Never pass a password on the
command line: scenario fields use `"depuis_secrets"` plus `secret_cle`, and
the credential is resolved inside Playwright.

**--no-evaluer**
: Refuse the **evaluer** action for the whole run — arbitrary JavaScript is
not executed on the target page.

**--no-filtre-evaluer**
: Disable stdout neutralisation of **evaluer** return values, URLs and error
messages — explicit debug runs only. Neutralisation is on by default; when
disabled, `boussole.filtre_evaluer_actif: false` is set in the output so the
operator can audit it from the JSON itself.

**--replay-verifier** *FILE*
: Compare the current run against a saved reference and exit non-zero on
divergence. The reference is written by **--sauver-verifier-reference**.
**rpa.py** only.

# FILES

**/etc/dinoer/dinoer.conf**
: Configuration read by **campagne.py** and the credential resolver.
Created by the operator, never generated automatically. The **DINOER_CONF**
environment variable overrides this path. `secrets_dir` inside it points at
the mounted credentials directory.

**/opt/dinoer/**
: Application code, the Python virtual environment, and the documentation
that the commands themselves refer to.

**/opt/dinoer/docs/GUIDE_LLM.md**
: The entry point an agent is required to read. **MANUEL.md** in the same
directory holds the exact commands with real paths.

**/var/log/dinoer/**
: Append-only operation log (`operations.jsonl`) and the structured
evidence directory. Preserved across re-deployments.

**/tmp/dinoer/**
: Ephemeral per-run working directory, cleared on reboot.

# EXIT STATUS

**0**
: The run completed. Note that an HTTP 404 or 403 on the target is reported
in the JSON, not as a failure of the command.

**1**
: The run failed, or the guide-read pre-flight was not satisfied
(*guide_non_lu*).

**2**
: Incompatible arguments, rejected before any browser was started.

**42**
: The credentials directory is closed, or a credentials file failed its
integrity checksum. Mount it with **scripts/monter-repertoire-chiffre.sh**,
or inspect the credentials file if the message names a checksum mismatch.

**43**
: No **secrets_dir** configured. Configure it in **dinoer.conf**, or point
**DINOER_CONF** at a project-specific configuration file.

# EXAMPLES

Capture a page with the accessibility tree:

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
        --url https://example.com --a11y --guide-version 1.3

Read only the state of a page, without executing any action:

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
        --url https://example.com --guide-version 1.3

Reach an administration panel that refreshes statistics continuously:

    /opt/dinoer/venv/bin/python /opt/dinoer/shot.py \
        --url http://target.local/ --wait-until load --a11y

Run a scenario with credentials from an explicit file:

    /opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
        --scenario ./login.json --secrets ~/Vaults/project/creds.json

Check that a page has not structurally regressed:

    bash scripts/monitor-verifier.sh --scenario ./page.json --reference ./page.ref.json

Read the operation log for a target:

    /opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible example.com --format json

# SEE ALSO

Full documentation is installed with the package:
**/opt/dinoer/docs/MANUEL.md** for the operator manual,
**/opt/dinoer/docs/GUIDE_LLM.md** for the agent-facing guide,
**/opt/dinoer/docs/FAQ_LLM.md** for capability-by-version answers.
