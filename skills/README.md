# Skills — Mémoire procédurale Dinoer (v1.6.0)

Un **skill** est un scénario promu : un parcours qui a réussi en conditions réelles
et a été extrait du journal pour être rejoué sans réanalyser l'interface.

## Format

Un skill est un fichier JSON au même format qu'un scénario `scenarios/*.json` :

```json
{
  "nom": "connexion_sillage",
  "description": "Connexion admin Sillage depuis la page de login",
  "url": "https://mon-app.local/",
  "actions": [
    {"type": "remplir", "selecteur": "input[name=\"password\"]", "valeur": "depuis_secrets", "secret_cle": "password"},
    {"type": "cliquer", "selecteur": "button[type=submit]"}
  ]
}
```

Les champs `description` et `nom` sont requis pour distinguer un skill d'un scénario jetable.

## Créer un skill depuis le journal

Après un run réussi, récupérer son `operation_id` dans le journal :

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py --cible mon-app.local --limite 5
```

Puis exporter :

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/journal.py \
  --exporter-skill a1b2c3d4e5f6 \
  --nom connexion_sillage
```

Le fichier `skills/connexion_sillage.json` est créé et peut être rejoué via `rpa.py`.

## Rejouer un skill

```bash
/opt/dinoer/venv/bin/python /opt/dinoer/rpa.py \
  --scenario /opt/dinoer/skills/connexion_sillage.json
```

## Règles

- Un skill ne contient jamais de credentials en clair — toujours `"valeur": "depuis_secrets"`.
- Les sélecteurs CSS ne sont valables que si l'interface n'a pas changé depuis la validation.
- Ajouter `derniere_validation` (date ISO) dans le JSON lors des rejeux réussis.