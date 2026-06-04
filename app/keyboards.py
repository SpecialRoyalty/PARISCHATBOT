from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

def admin_panel(is_super=False):
    rows=[[InlineKeyboardButton(text='🏟 Créer pronostic', callback_data='admin:create')],
          [InlineKeyboardButton(text='📊 Matchs actifs', callback_data='admin:active'), InlineKeyboardButton(text='✅ Matchs clôturés', callback_data='admin:closed')],
          [InlineKeyboardButton(text='📌 Règles', callback_data='admin:rules'), InlineKeyboardButton(text='🚫 Mots interdits', callback_data='admin:words')],
          [InlineKeyboardButton(text='🔒 Fermer groupe', callback_data='admin:close_group'), InlineKeyboardButton(text='🔓 Ouvrir groupe', callback_data='admin:open_group')],
          [InlineKeyboardButton(text='ℹ️ Info', callback_data='admin:info')]]
    if is_super:
        rows += [[InlineKeyboardButton(text='👑 Admins/Trusted', callback_data='admin:roles')],
                 [InlineKeyboardButton(text='👋 Config /start', callback_data='admin:startcfg')],
                 [InlineKeyboardButton(text='🧾 Logs', callback_data='admin:logs')]]
    return InlineKeyboardMarkup(inline_keyboard=rows)

def match_vote_group(bot_username: str, match_id: int):
    url=f'https://t.me/{bot_username}?start=vote_{match_id}' if bot_username else None
    btn=InlineKeyboardButton(text='Je pronostique', url=url) if url else InlineKeyboardButton(text='Je pronostique', callback_data=f'vote:{match_id}')
    return InlineKeyboardMarkup(inline_keyboard=[[btn]])

def active_matches(matches):
    rows=[[InlineKeyboardButton(text=m.title, callback_data=f'openmatch:{m.id}')] for m in matches]
    return InlineKeyboardMarkup(inline_keyboard=rows or [[InlineKeyboardButton(text='Aucun pronostic actif', callback_data='noop')]])

def winner_keyboard(match):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=match.option_a, callback_data=f'pick:{match.id}:a')],
        [InlineKeyboardButton(text=match.option_b, callback_data=f'pick:{match.id}:b')],
        [InlineKeyboardButton(text='🤝 Match nul', callback_data=f'pick:{match.id}:draw')],
    ])

def score_skip(match_id:int):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='Je ne sais pas', callback_data=f'score_skip:{match_id}')]])

def close_result(match):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=match.option_a, callback_data=f'result:{match.id}:a')],
        [InlineKeyboardButton(text=match.option_b, callback_data=f'result:{match.id}:b')],
        [InlineKeyboardButton(text='🤝 Match nul', callback_data=f'result:{match.id}:draw')],
        [InlineKeyboardButton(text='🚫 Annulé', callback_data=f'result:{match.id}:cancel')],
    ])
