def anonymize(name: str | None) -> str:
    if not name: return 'Me****re'
    name=str(name)
    if len(name)<=2: return name[0]+'*'
    if len(name)<=4: return name[0]+'**'+name[-1]
    return name[:2]+'****'+name[-1]

def parse_title(title:str):
    for sep in [' vs ', ' VS ', ' Vs ', ' - ', ' contre ']:
        if sep in title:
            a,b=title.split(sep,1); return a.strip(), b.strip()
    return title.strip(), 'Adversaire'
