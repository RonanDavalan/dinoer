# Changelog

Generated from `debian/changelog` at build time — do not edit by hand.
Edit `debian/changelog` and rebuild instead
(`bash ~/git/Dinoer/scripts/construire-paquet.sh`).

## 1.0.0 — 15 Aug 2026 00:22:11 +0200

- Initial dinoer .deb packaging, adapted from the diwall channel this package is forked from (Dinoer split off Diwall on 2026-07-25, diwall's own .deb history predates the fork and lives in Diwall's own changelog, not repeated here).
- Renamed throughout: package/source name, /opt/dinoer install path, dinoer system user/group, /etc/dinoer config directory, /var/log/dinoer journal + evidence directory, the six /usr/bin/dinoer-* wrapper commands and their man pages (corrected 15/08/2026, was documented as five — contradicted by this same changelog's own next entry, which counts dinoer-campaign as the sixth).
- Dropped dinoer-watch (watch.py and the whole SoM/vision perception layer it depended on do not exist in Dinoer — removed from the product on 2026-08-09, FONDATION_DINOER.md §4). No replacement wrapper: Dinoer's structural monitoring lives in dinoer-monitor-verifier instead, already present.
- Added campagne.py + the new dinoer-campaign wrapper (research pipeline entry point, absent from Diwall) to debian/dinoer.install. Verified against the wrapper's own source, not assumed by analogy: campagne.py never reads DINOER_CONF (it resolves its own paths via dedicated env vars — DINOER_CAMPAGNES_DIR, DINOER_SEARXNG_URL, DINOER_TABLES_REFERENCE, DINOER_JOURNAL), so dinoer-campaign does not export it, unlike dinoer-shot/dinoer-rpa.
- debian/dinoer.install's lib/*.py list rebuilt from the lib/ actually on disk today, not copied from the old diwall.install: dropped lib/vision.py (removed with SoM), added the seven modules of the deep-research pipeline (cache_recherche.py, extraction.py, fetch_leger.py, searxng.py, selection_candidats.py, synthese.py, tables_reference.py) that diwall.install never listed even before the fork, plus scenarios/*.json and docs/images/*.png resynced against what's actually referenced (dead SoM screenshot examples dropped, nothing in docs/ links to them any more).

