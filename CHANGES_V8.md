# Corrections V8

- `/start` est traité uniquement en privé.
- Dans le groupe, `/start` et toute commande non autorisée sont supprimés immédiatement.
- Utilisateur normal qui utilise une commande dans le groupe : sanction silencieuse.
- Admin / Trusted / Super Admin qui utilise une commande non autorisée : suppression silencieuse, pas de sanction.
- Commandes autorisées dans le groupe : `/supprime` et `/ban` pour Admin / Trusted / Super Admin.
- Super Admin voit : Panel Super Admin, Panel Admin, Panel Trusted, Panel utilisateur.
- Admin voit : Panel Admin, Panel utilisateur.
- Trusted voit : Panel Trusted, Panel utilisateur.
- Admin Panel ne contient plus le bouton Panel Trusted.
