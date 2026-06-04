import re

def anonymize(name: str | None, user_id: int | None = None) -> str:
    base = name or (str(user_id) if user_id else 'Utilisateur')
    if len(base) <= 2:
        return base[0] + '*'
    return base[:2] + ('*' * max(3, len(base)-3)) + base[-1]

def split_title(title: str) -> tuple[str,str]:
    for sep in [' vs ', ' VS ', ' v ', ' - ', ' contre ']:
        if sep in title:
            a,b=title.split(sep,1)
            return a.strip(), b.strip()
    return 'Équipe A', 'Équipe B'

def has_link(text: str | None) -> bool:
    if not text: return False
    patterns=[r'https?://', r'\bt\.me/', r'telegram\.me/', r'www\.', r'\b[a-z0-9-]+\.(com|net|org|io|fr|gg|me|co)\b']
    return any(re.search(p, text.lower()) for p in patterns)

def valid_score(s: str) -> bool:
    return bool(re.fullmatch(r'\d{1,2}\s*[-:]\s*\d{1,2}', s.strip()))
