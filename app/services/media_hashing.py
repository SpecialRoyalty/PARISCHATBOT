from __future__ import annotations
import hashlib
from io import BytesIO
from aiogram import Bot
from aiogram.types import Message

VIDEO_PREFIX_BYTES = 2 * 1024 * 1024

def _pick_media(message: Message):
    if message.photo:
        return message.photo[-1].file_id, 'image'
    if message.video:
        return message.video.file_id, 'video'
    if message.animation:
        return message.animation.file_id, 'video'
    if message.document:
        mt = message.document.mime_type or ''
        kind = 'image' if mt.startswith('image/') else 'video' if mt.startswith('video/') else 'file'
        return message.document.file_id, kind
    if message.sticker:
        return message.sticker.file_id, 'image'
    return None, None

async def compute_media_hash(bot: Bot, message: Message) -> str | None:
    """Calcule un vrai hash.

    - Image/sticker/document image : SHA-256 du fichier complet.
    - Vidéo/animation/document vidéo : SHA-256 du premier segment téléchargé.
      Telegram ne permet pas toujours un range HTTP propre via toutes les libs,
      donc on télécharge via Bot API puis on ne conserve/hash que le préfixe.
    - Autre document : SHA-256 du fichier complet.
    """
    file_id, kind = _pick_media(message)
    if not file_id:
        return None
    buff = BytesIO()
    await bot.download(file_id, destination=buff)
    data = buff.getvalue()
    if kind == 'video':
        data = data[:VIDEO_PREFIX_BYTES]
    prefix = {'image': 'img', 'video': 'vid', 'file': 'file'}.get(kind, 'media')
    return f"{prefix}:sha256:{hashlib.sha256(data).hexdigest()}"
