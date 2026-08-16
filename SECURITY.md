# Security Policy

Dinoer handles credentials (via the encrypted secrets directory) and, on its
heavy-tier escalation path, drives a real browser session. A vulnerability
here has a real cost for whoever runs it — this policy exists so it gets
reported before it gets exploited.

This policy was written ahead of the first release — declare before the
first incident, not after — since 15/08/2026, a real `.deb 1.0.0-1` release
exists, so it now applies in practice, not just in principle.

## Supported versions

Only the latest published release is supported. Dinoer does not maintain
parallel maintenance branches; a fix lands in the next release, not as a
backport to an older tag.

## Reporting a vulnerability

**Do not open a public GitHub issue.** A public issue discloses the
vulnerability before a fix exists, exposing everyone currently running
Dinoer.

Report privately via **GitHub Security Advisories** on the Dinoer
repository once it is public. Until then, contact the maintainer directly.

If that path is unavailable to you, open a regular issue asking for an
alternate private contact — do not include vulnerability details in it.

## What to expect

- Acknowledgement within **72 hours**.
- A good-faith, coordinated disclosure is never met with legal action —
  report responsibly and it stays that way.
- Fixes ship as a normal release once verified; the report stays private
  until then, and credit is given in the release notes if you want it.

## Scope

This policy covers the code in this repository: `shot.py`, `rpa.py`,
`campagne.py`, `journal.py`, and everything under `lib/`. It does not cover:

- Unofficial forks or modified copies.
- Versions predating the current release — see "Supported versions" above.
- Diwall, the sibling project this repository was forked from — a separate
  codebase with its own security policy.
