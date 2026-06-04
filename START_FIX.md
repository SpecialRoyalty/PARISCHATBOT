# Fix /start silencieux

Cause: des handlers privés trop larges dans admin/social interceptaient tous les messages privés, y compris `/start`, puis retournaient sans réponse.

Correction:
- handlers admin limités aux utilisateurs ayant un état admin actif
- handlers suggestion limités aux utilisateurs ayant une suggestion active
- handler score limité aux utilisateurs en attente de score
- log explicite quand `/start` est reçu

Note Railway/Telegram: l'erreur `Conflict: terminated by other getUpdates request` signifie qu'une autre instance du même bot tourne encore. Il faut garder un seul service actif pour ce BOT_TOKEN.
