# Cahier des charges implémenté

## Utilisateurs
- `/start` privé.
- Message d'accueil configurable.
- Liste des pronostics actifs.
- Vote privé sur un match actif.
- Choix : équipe A, équipe B, match nul.
- Score exact ou `Je ne sais pas`.
- Une seule participation par match.
- Tendance mise à jour immédiatement après chaque vote.
- Quand les votes ferment, la tendance et le message de pronostic disparaissent.

## Groupe
- Publication d'un pronostic avec image.
- Bouton `Je pronostique` en deep-link privé.
- Publication d'une tendance unique avec image.
- Classement automatique toutes les 5h.
- Règles automatiques toutes les 2h.
- Message partage toutes les 3h.
- Message suggestion toutes les 6h.

## Admins
- Panel bouton pour admins/super admins.
- Création match : catégorie, image, titre, dates.
- Match nul toujours actif.
- Fermeture/ouverture groupe.
- Gestion règles.
- Ajout mots interdits.
- Clôture résultat des matchs verrouillés.
- Info diagnostic.

## Super Admins
- Panel complet.
- Logs.
- Configuration texte de bienvenue.
- Rôles chargés depuis variables Railway.

## Modération
- Liens interdits = ban immédiat.
- Mots interdits = mute 1j, mute 3j, puis ban.
- Commandes `/` en groupe = mute 10j puis ban.
- `/supprime` et `/ban` pour Admins/Trusted IDs.
- `/ban` en réponse à un média ajoute son hash réel.
- Images : SHA-256 fichier complet.
- Vidéos : SHA-256 premier Mo téléchargé.
- Suppression ciblée des notifications entrée/sortie.
- Groupe unique autorisé.

## Invitations
- Bouton partage.
- Lien unique par utilisateur.
- Comptage lorsque Telegram fournit le lien d'invitation dans l'événement d'entrée.

## Données
- Users, matches, predictions, settings, forbidden words, sanctions, media hashes, invite links, suggestions, identity history, security logs.
