from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from app.keyboards.common import kb

def match_vote_url(bot_username:str, mid:int):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text='👇 Je pronostique', url=f'https://t.me/{bot_username}?start=vote_{mid}')]])

def active_matches_kb(matches):
    rows=[]
    for m in matches:
        rows.append([(f'🏟 #{m.id} {m.title}', f'user:open_match:{m.id}')])
    rows.append([('⬅ Retour','nav:user')])
    return kb(rows)

def choose_winner_kb(mid:int, team_a:str, team_b:str):
    return kb([[(team_a, f'vote:{mid}:a')],[(team_b, f'vote:{mid}:b')],[('🤝 Match nul', f'vote:{mid}:draw')],[('⬅ Retour','user:matches')]])

def score_kb(mid:int): return kb([[('Je ne sais pas', f'score:{mid}:skip')]])

def close_result_kb(mid:int, team_a:str, team_b:str):
    return kb([[(team_a, f'close:{mid}:a')],[(team_b, f'close:{mid}:b')],[('🤝 Match nul', f'close:{mid}:draw')],[('🚫 Annulé', f'close:{mid}:cancel')]])
