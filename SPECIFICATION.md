# Cahier des charges implémenté

## Pronostics
- Création match via boutons admin.
- Catégories : Foot, Basket, Tennis, Boxe, Autre.
- Image obligatoire lors de la création.
- Titre direct : `France 🇫🇷 vs Côte d’Ivoire 🇨🇮`.
- Détection automatique des deux participants depuis le titre.
- Message avec jour, mois, année, heure.
- Bouton `Je pronostique`.
- Republication toutes les 30 minutes avec suppression de l’ancien.
- Fermeture automatique au début du match.
- `/start` privé liste les pronostics en cours et permet de voter.

## Vote
- Privé uniquement.
- Choix participant A / participant B / match nul.
- Match nul toujours actif.
- Score exact au format `2-1` ou `Je ne sais pas`.
- Un vote par Telegram user ID.
- Vote bloqué après début.

## Tendances
- Message avec image.
- Nombre de participants.
- Pourcentages A/B/Nul.
- Nombre de membres du Top 10 ayant participé.
- Appel à pronostiquer.
- Fréquence adaptative : <50 = 2h, 50-200 = 1h, >200 = 30min.
- Suppression de l’ancien message tendance.

## Clôture
- Admin choisit gagnant ou annulé.
- Score final demandé.
- Calcul taux réussite, participations, scores exacts.
- Badges mis à jour.

## Classement
- Pas de points.
- Classement par taux réussite, participations, scores exacts.
- Minimum 10 participations.
- Publication toutes les 5h.
- Suppression après 1h.
- Pseudos anonymisés.

## Badges
- Expert Sport, Légende, Tireur d’élite, En feu, Série légendaire.
- Actif, Régulier, Vétéran.
- Suggestions et invitations prévus dans le modèle.

## Invitations
- Message partage toutes les 3h.
- Lien unique par utilisateur.
- Comptage des arrivées via lien.
- Top inviteurs à 12h.
- Suppression après 1h.

## Suggestions
- Message toutes les 6h.
- Parcours privé : catégorie, titre, date, image optionnelle.
- Admin reçoit Accepter / Refuser / Demander précision.

## Règles
- Texte configurable par admin.
- Publication toutes les 2h.
- Remplacement automatique.

## Sécurité et modération
- Groupe autorisé unique : `-1003996641790`.
- Tentative d’utilisation ailleurs : alerte admins + sortie du groupe.
- Super Admins / Admins / Trusted IDs.
- Ajout/retrait Admin et Trusted depuis panel Super Admin.
- Trusted IDs limités à `/supprime` et `/ban`.
- Tout lien interdit : suppression + ban immédiat.
- Mots interdits : mute 1j, mute 3j, ban.
- Commandes `/` utilisateurs : mute 10j puis ban.
- Ajout de bots interdit.
- Notifications entrée/sortie supprimées.
- Médias interdits mémorisés via identifiant unique Telegram.
- Changements pseudo/username signalés publiquement avec anonymisation et cooldown 12h.
- Logs sécurité en base.

## Info Super Admin
- Bouton Info : bot, DB, process Railway, scheduler, envoi messages, groupe, version.


## Hash média production

Le bot ne se limite plus à file_unique_id. Il télécharge le média via Telegram Bot API et calcule :
- image : SHA-256 du fichier complet ;
- vidéo / animation : SHA-256 du premier segment vidéo téléchargé ;
- document : SHA-256 du fichier selon son type.

Le mot technique n'est jamais affiché publiquement.
