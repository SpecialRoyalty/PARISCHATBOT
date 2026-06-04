# Sport Prono Bot Telegram — Railway

Bot Telegram complet pour groupe sport/pronostics avec panel admin à boutons, PostgreSQL et tâches planifiées.

## Déploiement Railway

1. Créer un bot via BotFather et récupérer `BOT_TOKEN`.
2. Créer un projet Railway avec PostgreSQL.
3. Ajouter les variables de `.env.example`.
4. Déployer le repo/ZIP sur Railway.
5. Ajouter le bot comme administrateur du groupe `-1003996641790` avec droits : supprimer messages, bannir, restreindre, gérer invitations, gérer permissions.
6. Envoyer `/admin` en privé au bot depuis un Super Admin.

## Variables obligatoires

- `BOT_TOKEN`
- `DATABASE_URL`
- `GROUP_ID=-1003996641790`
- `SUPER_ADMIN_IDS`
- `ADMIN_IDS`
- `TRUSTED_IDS`

## Commandes

Utilisateurs :
- `/start` en privé : affiche tous les pronostics en cours.

Admins :
- `/admin` ou `/panel` en privé : ouvre le panel à boutons.

Trusted IDs :
- `/supprime` en réponse à un message : supprime silencieusement.
- `/ban` en réponse à un membre/média : ban silencieux et mémorise le média interdit si présent.

## Notes importantes

- Les dates de création de match sont saisies au format `YYYY-MM-DD HH:MM`.
- Le bot utilise PostgreSQL via SQLAlchemy async.
- Les tables sont créées automatiquement au lancement.
- Le bot fonctionne en polling, adapté à Railway worker.


## Production v3

Cette version ajoute le hash média réel :
- images : SHA-256 du fichier téléchargé complet ;
- vidéos/animations : SHA-256 du premier segment de 2 Mo ;
- documents : SHA-256 selon type.

Commandes utiles :
```bash
python -m compileall app
pytest
```

Alembic est inclus. Par défaut, le bot peut créer les tables automatiquement au boot, mais pour une production stricte, utilisez les migrations.

## Correctif Railway PostgreSQL
Cette version convertit automatiquement `DATABASE_URL=postgresql://...` ou `postgres://...` en `postgresql+asyncpg://...` pour éviter l'erreur `ModuleNotFoundError: No module named psycopg2` avec SQLAlchemy async.

## Correctif v6

- Les IDs admin/super admin/trusted acceptent maintenant les guillemets Railway, exemple `SUPER_ADMIN_IDS="5296696302"`.
- `/start` reconnaît les Super Admins/Admins et affiche directement le panel.
- Les nouveaux utilisateurs non-admin reçoivent au premier `/start` un message d'accueil configurable + photo configurable, puis la liste des pronostics en cours.
- Configuration du message/photo d'accueil : Panel Super Admin > 👋 Config message /start.
