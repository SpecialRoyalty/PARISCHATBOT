from datetime import datetime
FORMATS=['%Y-%m-%d %H:%M','%d/%m/%Y %H:%M','%d-%m-%Y %H:%M']
def parse_dt(text:str):
    text=text.strip()
    for f in FORMATS:
        try: return datetime.strptime(text,f)
        except ValueError: pass
    raise ValueError('Format attendu : 2026-06-15 22:00')
