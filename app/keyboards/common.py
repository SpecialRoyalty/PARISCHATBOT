from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
CATEGORIES = [('⚽ Foot','Foot'),('🏀 Basket','Basket'),('🎾 Tennis','Tennis'),('🥊 Boxe','Boxe'),('🥋 MMA','MMA'),('📦 Autre','Autre')]

def kb(rows):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=t, callback_data=d) for t,d in row] for row in rows])

def category_kb(prefix='cat'):
    return kb([[(t,f'{prefix}:{v}')] for t,v in CATEGORIES]+[[('⬅ Retour','back')]])

def user_panel():
    return kb([[('🏟 Pronostics en cours','user:matches')],[('🏆 Classement','user:leaderboard'),('🎖 Mes badges','user:badges')],[('📈 Mes statistiques','user:stats')],[('📢 Inviter des amis','user:share')],[('💡 Suggérer un match','user:suggest')],[('📜 Règlement','user:rules')]])

def trusted_panel():
    return kb([[('➕ Proposer un match','trusted:propose')],[('➕ Ajouter un mot interdit','trusted:add_word')],[('⚔ Commandes Trusted','trusted:commands')],[('📊 Mes propositions','trusted:my_requests')],[('👤 Panel utilisateur','nav:user')],[('⬅ Retour','back')]])

def admin_panel():
    return kb([[('➕ Créer match','admin:create')],[('📋 Matchs actifs','admin:active'),('📁 Matchs clôturés','admin:closed')],[('📊 Statistiques','admin:stats')],[('📨 Demandes Trusted','admin:trusted_requests')],[('💡 Suggestions utilisateurs','admin:suggestions')],[('🚫 Mots interdits','admin:words')],[('📜 Règlement','admin:rules')],[('🔒 Fermer groupe','admin:close_group'),('🔓 Ouvrir groupe','admin:open_group')],[('👤 Panel utilisateur','nav:user')]])

def super_panel():
    return kb([[('👥 Gestion Admins','super:admins'),('🤝 Gestion Trusted','super:trusted')],[('📢 Broadcast Groupe','super:broadcast_group')],[('📨 Broadcast Privé','super:broadcast_private')],[('🎯 Broadcast Catégorie','super:broadcast_category')],[('🖼 Photo /start','super:start_photo'),('📝 Texte /start','super:start_text')],[('🚫 Médias interdits','super:hashes'),('📜 Logs sécurité','super:logs')],[('📊 Info système','super:info'),('⏱ Fréquences','super:freq')],[('🛡 Panel Admin','nav:admin'),('🤝 Panel Trusted','nav:trusted')],[('👤 Panel utilisateur','nav:user')]])

def role_choice(is_super=False, is_admin=False, is_trusted=False):
    rows=[]
    # Super Admin voit tout.
    if is_super:
        rows.append([('👑 Panel Super Admin','nav:super')])
        rows.append([('🛡 Panel Admin','nav:admin')])
        rows.append([('🤝 Panel Trusted','nav:trusted')])
    # Admin : panel admin + utilisateur uniquement.
    elif is_admin:
        rows.append([('🛡 Panel Admin','nav:admin')])
    # Trusted : panel trusted + utilisateur uniquement.
    elif is_trusted:
        rows.append([('🤝 Panel Trusted','nav:trusted')])
    rows.append([('👤 Panel utilisateur','nav:user')])
    return kb(rows)
