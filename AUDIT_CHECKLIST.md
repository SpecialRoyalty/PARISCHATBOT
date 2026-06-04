# Audit checklist v4

Audit réalisé localement avant création ZIP.

## Vérifications techniques

- [x] Archive ZIP créée depuis les fichiers corrigés
- [x] `python -m compileall -q app tests` OK
- [x] Imports principaux OK avec variables de test
- [x] `pytest -q` OK : 4 tests passent
- [x] Erreur bloquante `from typing import set` corrigée
- [x] `ChatPermissions` mis à jour pour aiogram 3 / Bot API récent
- [x] Migration Alembic initiale non vide : crée/drop toutes les tables via metadata

## Fonctionnalités cahier des charges

- [x] Railway : Procfile, Dockerfile, railway.json, runtime, requirements
- [x] Variables d'environnement : BOT_TOKEN, DATABASE_URL, GROUP_ID, SUPER_ADMIN_IDS, ADMIN_IDS, TRUSTED_IDS, fréquences
- [x] Groupe unique verrouillé sur `-1003996641790`
- [x] Alerte admins/super admins si bot ajouté hors groupe autorisé
- [x] `/start` privé : liste les pronostics actifs et permet de voter
- [x] Panel admin à boutons
- [x] Super Admin : ajout/retrait Admin, ajout/retrait Trusted, logs, settings, info
- [x] Admin : création match, règles, mots interdits, stats, matchs en cours/clôturés, ouvrir/fermer groupe
- [x] Trusted IDs : uniquement `/supprime` et `/ban`
- [x] Création match : catégorie, image, titre, date début, date fin
- [x] Publication match avec image et bouton Je pronostique
- [x] Date affichée avec jour/mois/année/heure
- [x] Match nul toujours actif
- [x] Vote privé : vainqueur + score exact ou je ne sais pas
- [x] Vote unique par utilisateur/match
- [x] Votes verrouillés au début du match
- [x] Tendance avec image, participants, %, Top 10, appel à pronostiquer
- [x] Tendance adaptative : <50 = 2h, 50-200 = 1h, >200 = 30min
- [x] Publication pronostic toutes les 30 min avec suppression ancien message
- [x] Suppression pronostic/tendance au début du match
- [x] Notification admin pour clôturer
- [x] Clôture : gagnant / nul / annulé + score exact
- [x] Classement sans points : taux de réussite + participations + scores exacts
- [x] Minimum classement configurable, par défaut 10 participations
- [x] Badges performance/participation/séries
- [x] Badges suggestions acceptées
- [x] Badges invitations
- [x] Message partage toutes les 3h + lien unique
- [x] Top inviteurs quotidien à 12h, suppression après 1h
- [x] Suggestion match : parcours utilisateur + boutons admin accepter/refuser/demander précision
- [x] Règles automatiques toutes les 2h, ancien message supprimé
- [x] Fermer/Ouvrir groupe par panel
- [x] Mots interdits : mute 1j, 3j, puis ban
- [x] Tout lien interdit : suppression + ban immédiat
- [x] Médias interdits : hash réel SHA-256 image complète / premier segment vidéo
- [x] `/ban` sur média : calcule et stocke le hash réel
- [x] Suppression notifications entrée/sortie
- [x] Ajout de bot interdit
- [x] Commandes utilisateurs `/...` : mute 10j puis ban
- [x] Surveillance changement pseudo/username avec annonce publique limitée à 12h
- [x] Logs sécurité
- [x] Bouton Info : DB + envoi message test + version + groupe

## Limites honnêtes restantes

- Ce projet n'a pas été testé contre Telegram/Railway en conditions réelles depuis ce sandbox.
- Le hash vidéo télécharge le fichier via Bot API puis hashe le préfixe en mémoire ; pour de très grosses vidéos, prévoir un stockage temporaire/streaming si Telegram autorise de très gros médias.
- Les erreurs réseau Telegram sont parfois journalisées ou ignorées pour éviter de bloquer le bot, mais une stack d'observabilité externe reste recommandée en production réelle.
