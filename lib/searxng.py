"""
searxng.py — Interrogation HTTP pure de l'API JSON de SearXNG.

Palier de découverte du pipeline de recherche profonde (DINOER_RESEARCH.md
§3.1). Aucune dépendance à Playwright : SearXNG expose une API JSON native,
une requête HTTP suffit — le navigateur ne doit jamais être engagé pour
cette primitive (principe d'architecture, DINOER_RESEARCH.md §2). Ne
présuppose aucune co-localisation avec Dinoer : SearXNG peut tourner sur
une autre machine du réseau (ex. une machine dédiée pendant que Dinoer
s'exécute sur la machine de développement/production).

Résolution de l'URL du métamoteur (par ordre de priorité) :
  1. DINOER_SEARXNG_URL (variable d'environnement)
  2. Clé "searxng_url" dans /opt/dinoer/dinoer.conf (JSON)

Pas de défaut public, contrairement à `lib/ntfy.py` (ntfy.sh) : il n'existe
pas d'instance SearXNG publique fiable à supposer sans consentement de
l'opérateur — interroger silencieusement un service tiers non choisi serait
une mauvaise surprise, pas une commodité.

Dépendance optionnelle : requests (non requise pour l'import).
"""
import json
import os
import sys

_CONF_PATH = "/opt/dinoer/dinoer.conf"


class SearxngNonConfigureError(Exception):
    """Aucune URL SearXNG résolue — ni DINOER_SEARXNG_URL, ni dinoer.conf.

    Levée immédiatement (pas de dégradation silencieuse) : contrairement à
    une panne réseau ponctuelle sur une URL déjà connue (absorbée par
    `rechercher()` en liste vide), une configuration manquante doit être
    visible et corrigée avant toute campagne de collecte.
    """


def _url_searxng() -> str:
    if "DINOER_SEARXNG_URL" in os.environ:
        return os.environ["DINOER_SEARXNG_URL"].rstrip("/")

    if os.path.isfile(_CONF_PATH):
        try:
            with open(_CONF_PATH, encoding="utf-8") as f:
                conf = json.load(f)
            if "searxng_url" in conf:
                return conf["searxng_url"].rstrip("/")
        except (OSError, json.JSONDecodeError):
            pass

    raise SearxngNonConfigureError(
        "Aucune URL SearXNG configurée.\n"
        "  Définir DINOER_SEARXNG_URL=https://votre-instance/ , ou ajouter "
        f"la clé \"searxng_url\" dans {_CONF_PATH}."
    )


def rechercher(
    requete: str,
    page: int = 1,
    timeout: int = 10,
    langue: str = "fr-FR",
    url_searxng: str = None,
) -> list[str]:
    """Interroge l'API JSON de SearXNG, retourne la liste des URLs résultats.

    Adapté de `Sentinelle/collecteur/module1_collecte.py::interroger_searxng()`
    (cf. DINOER_RESEARCH.md §3.1 et §1). Les erreurs réseau/HTTP sont
    journalisées sur stderr et absorbées en liste vide plutôt que levées :
    une campagne de collecte ne doit jamais s'interrompre entièrement pour
    un métamoteur momentanément indisponible sur une seule requête.

    Lève `SearxngNonConfigureError` si `url_searxng` n'est pas fourni et
    qu'aucune configuration n'est résolue — une erreur de configuration,
    à la différence d'une panne réseau, doit interrompre l'appelant.
    """
    import requests

    base = (url_searxng or _url_searxng()).rstrip("/")
    params = {
        "q": requete,
        "format": "json",
        "pageno": page,
        "categories": "general",
        "language": langue,
    }
    url_complete = f"{base}/search"

    try:
        resp = requests.get(url_complete, params=params, timeout=timeout)
        resp.raise_for_status()
        donnees = resp.json()
        return [r.get("url", "") for r in donnees.get("results", []) if r.get("url")]
    except requests.exceptions.SSLError as e:
        print(f"⚠ Dinoer : erreur SSL SearXNG ({e})", file=sys.stderr)
    except requests.exceptions.ConnectionError as e:
        print(f"⚠ Dinoer : connexion SearXNG impossible sur {url_complete} ({e})", file=sys.stderr)
    except requests.exceptions.HTTPError as e:
        print(f"⚠ Dinoer : erreur HTTP SearXNG ({e})", file=sys.stderr)
    except (requests.exceptions.RequestException, ValueError) as e:
        print(f"⚠ Dinoer : erreur SearXNG inattendue ({type(e).__name__} : {e})", file=sys.stderr)
    return []
