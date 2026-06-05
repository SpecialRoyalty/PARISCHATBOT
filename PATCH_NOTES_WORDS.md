# Patch mots interdits

Corrige l'erreur `MultipleResultsFound` lors de l'ajout d'un mot interdit.

Cause : la base contenait déjà plusieurs lignes correspondant au même mot en insensible à la casse, par exemple `vip`, `Vip`, `VIP`. La fonction utilisait `scalar_one_or_none()` et crashait si plusieurs lignes existaient.

Corrections :
- ajout mot interdit robuste avec `.first()` ;
- nettoyage automatique au démarrage des doublons insensibles à la casse ;
- suppression par bouton améliorée : après `Supprimer`, envoyer simplement l'ID, exemple `104` ;
- ancienne commande `supprimer mot 104` conservée ;
- messages d'erreur clairs si ID invalide ou mot déjà existant.

Le `#104` dans la liste est l'ID interne en base, normal et utile pour supprimer.
