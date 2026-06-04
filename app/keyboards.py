from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton


def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t,d in row] for row in rows])


def admin_panel(is_super: bool):
    rows = [
        [('➕ Créer pronostic','admin:create_match'), ('📋 Matchs en cours','admin:active_matches')],
        [('✅ Matchs clôturés','admin:closed_matches'), ('📊 Statistiques','admin:stats')],
        [('🚫 Mots interdits','admin:words'), ('📌 Règles','admin:rules')],
        [('🔒 Fermer groupe','admin:close_group'), ('🔓 Ouvrir groupe','admin:open_group')],
        [('🖼 Médias interdits','admin:media_hashes'), ('📊 Info','admin:info')],
    ]
    if is_super:
        rows += [
            [('👑 Ajouter Admin','super:add_admin'), ('🗑 Retirer Admin','super:remove_admin')],
            [('🛡 Ajouter Trusted','super:add_trusted'), ('🧹 Retirer Trusted','super:remove_trusted')],
            [('📜 Logs sécurité','super:logs'), ('⚙️ Paramètres','super:settings')],
            [('👋 Config message /start','super:welcome')],
        ]
    return kb(rows)


def category_kb(prefix='cat'):
    return kb([[('⚽ Foot',f'{prefix}:Foot'),('🏀 Basket',f'{prefix}:Basket')],[('🎾 Tennis',f'{prefix}:Tennis'),('🥊 Boxe',f'{prefix}:Boxe')],[('➕ Autre',f'{prefix}:Autre')]])


def match_vote_kb(match_id:int, bot_username: str | None = None):
    # Dans le groupe, on utilise un bouton URL deep-link.
    # Telegram ne permet pas d'envoyer un message privé à un utilisateur qui n'a jamais démarré le bot.
    # Le lien ouvre directement la conversation privée avec le bon match.
    if bot_username:
        return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Je pronostique', url=f'https://t.me/{bot_username}?start=vote_{match_id}')]])
    return kb([[('Je pronostique', f'vote:start:{match_id}')]])


def choice_kb(match_id:int, side_a:str, side_b:str):
    return kb([[ (side_a[:40], f'vote:choice:{match_id}:A') ],[(side_b[:40], f'vote:choice:{match_id}:B')],[('🤝 Match nul', f'vote:choice:{match_id}:DRAW')]])


def score_skip_kb(match_id:int):
    return kb([[('Je ne sais pas', f'vote:score_skip:{match_id}')]])


def active_matches_kb(matches):
    rows = [[(m.title[:48], f'vote:start:{m.id}')] for m in matches]
    return kb(rows or [[('Aucun pronostic en cours','noop')]])


def close_match_kb(match_id:int, side_a:str, side_b:str):
    return kb([[(side_a[:40], f'close:winner:{match_id}:A')],[(side_b[:40], f'close:winner:{match_id}:B')],[('🤝 Match nul', f'close:winner:{match_id}:DRAW')],[('🚫 Annulé', f'close:winner:{match_id}:CANCEL')]])


def suggestion_admin_kb(suggestion_id:int):
    return kb([[('✅ Accepter', f'sugg:accept:{suggestion_id}'),('❌ Refuser', f'sugg:refuse:{suggestion_id}')],[('❓ Demander précision', f'sugg:clarify:{suggestion_id}')]])
