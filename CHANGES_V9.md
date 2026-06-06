# V9 - Correction clôture résultat multi-admin

- La demande de résultat est envoyée une seule fois par match et par destinataire unique.
- Les destinataires sont dédupliqués si un ID est présent dans plusieurs rôles.
- La demande est envoyée aux Super Admins, Admins et Trusted.
- Le scheduler ne renvoie plus la même demande à chaque passage.
- Dès qu’un destinataire choisit un résultat, les demandes sont supprimées chez tous les autres.
- Ajout de la table `result_prompts` pour persister les messages de demande de résultat.
