# Dinoer — pense-bête

Version 1.0.0 — août 2026

Tout sur une page. Référence complète : `docs/MANUEL.md`.

---

## Trois commandes

```bash
# Voir une page : arbre d'accessibilité
/opt/dinoer/venv/bin/python /opt/dinoer/shot.py --url URL --a11y

# Exécuter un scénario
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py --scenario FICHIER.json

# Lire une référence de scénario et comparer (surveillance structurelle)
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario FICHIER.json --replay-verifier REF.json
```

Le premier appel sur une machine nécessite `--guide-version X.Y`, à lire avec
`grep notice-version /opt/dinoer/docs/GUIDE_LLM.md`.

---

## La boucle

```
        vous décidez de la suite
                  │
                  ▼
   ┌──────────────────────────────┐
   │  shot.py / rpa.py            │   un processus, un JSON sur stdout
   │    ├─ Chromium (headless)    │
   │    ├─ A11y : structure de page│
   │    └─ secrets : remplit les identifiants│  jamais dans le shell, jamais dans un log
   └──────────────┬───────────────┘
                  │  boussole + JSON
                  ▼
        vous lisez le même état
        que l'opérateur peut voir aussi
```

L'état de session vit dans un fichier, pas dans le processus : un second appel
avec `--reprendre-session` réutilise les cookies — jamais l'état du DOM.

---

## Lire la sortie dans cet ordre

| Lire | Vous dit |
|---|---|
| `succes` | l'exécution s'est-elle terminée |
| `boussole.url_courante` | où vous avez effectivement atterri |
| `boussole.dernier_code_http` | statut de la dernière navigation |
| `etat.pret_a_agir` + `etat.raisons` | frictions perçues — un rapport, jamais une barrière |
| `a11y_tree` | structure de la page — titres, champs, boutons |
| `respect` | votre propre empreinte : pages, actions, durée |

Si `boussole` ne correspond pas à votre attente, arrêtez-vous avant toute
action mutante.

---

## Chaque action

`type` est toujours requis. Les clés ci-dessous sont les clés additionnelles.

| Action | Requis | Optionnel |
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

## Identifiants — la seule forme correcte

```json
{"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"}
```

N'extrayez jamais un secret dans le shell. `lib/repertoire_chiffre.py` le
résout à l'intérieur du processus Playwright ; la valeur n'atteint jamais
votre ligne de commande, votre historique, ni aucun journal.

---

## Quand ça résiste

| Symptôme | Essayer |
|---|---|
| Le clic expire, élément visuellement caché | `"force": true`, puis `"repli_js": true` |
| Élément sous la ligne de flottaison | `defiler` d'abord |
| La page ne finit jamais de charger | `--wait-until load` |
| Le submit ne fait rien, aucune erreur | validation HTML native — soumettez le formulaire via `evaluer` |
| `exit 42` | répertoire chiffré non monté (`bash ~/git/Dinoer/Dinoer/scripts/monter-repertoire-chiffre.sh`), ou somme de contrôle des identifiants invalide (vérifiez le fichier d'identifiants) — les deux relèvent de `SecretsFermesError` |
| `guide_non_lu` | passez `--guide-version` une fois |
| 403 / 429 | lisez `respect.waf_bloquants` — un signal, pas une exception |

---

## Codes de sortie

`0` succès · `1` échec d'exécution ou assertion échouée · `2` arguments invalides (rejetés avant tout lancement de navigateur) · `3` mauvais interpréteur — utilisez le venv (`/opt/dinoer/venv/bin/python`) · `42` répertoire d'identifiants chiffré fermé, ou somme de contrôle des identifiants invalide (famille `SecretsFermesError`) · `43` aucun `secrets_dir` configuré (`SecretsNonConfigureError`).
