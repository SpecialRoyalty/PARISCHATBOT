# Audit v9 clean

Archive nettoyée pour Railway.

## Nettoyage effectué

- Suppression de `tests/`.
- Suppression de `pytest.ini`.
- Suppression de tous les `__pycache__/`.
- Suppression de tous les fichiers `.pyc`.
- Suppression de `pytest` et `aiosqlite` des dépendances production.

## Corrections ajoutées

- `/start vote_<match_id>` ouvre directement le pronostic demandé en privé.
- Après un vote enregistré, la tendance du match est recalculée et republiée immédiatement.
- Validation plus propre des IDs admin/trusted envoyés au panel.

## Vérifications effectuées

- Compilation Python complète OK avec variables d’environnement factices.
- Conversion Railway `postgresql://` vers `postgresql+asyncpg://` vérifiée.
- Parsing `SUPER_ADMIN_IDS="5296696302"` vérifié.
- Fichiers Railway présents à la racine : `start.sh`, `Procfile`, `railway.json`, `requirements.txt`.
