# Pronostic Sport Telegram Bot — Clean Final

Bot Telegram Railway + PostgreSQL pour pronostics sportifs, tendances, modération et panel admin.

## Déploiement Railway

1. Créer un projet Railway.
2. Ajouter PostgreSQL.
3. Uploader ce ZIP ou connecter le dépôt.
4. Variables obligatoires :

```env
BOT_TOKEN=
DATABASE_URL=
GROUP_ID=-1003996641790
SUPER_ADMIN_IDS=5296696302
ADMIN_IDS=
TRUSTED_IDS=
TIMEZONE=Europe/Paris
BOT_USERNAME=NomDuBotSansArobase
```

5. Donner au bot les droits admin dans le groupe :
- supprimer messages
- bannir utilisateurs
- restreindre utilisateurs
- gérer groupe
- gérer invitations

## Démarrage

Railway lance :

```bash
bash start.sh
```

## Notes importantes

- Le bot utilise PostgreSQL async. Les URL `postgresql://` Railway sont converties automatiquement en `postgresql+asyncpg://`.
- Les tables sont créées automatiquement au démarrage.
- Le bot est verrouillé sur `GROUP_ID`.
- Les messages d'entrée/sortie sont supprimés uniquement si Telegram les transmet comme messages service et si le bot a le droit de supprimer les messages.
