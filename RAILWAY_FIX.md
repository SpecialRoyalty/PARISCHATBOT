# Correctif Railway DB / Python

Cette version corrige l’erreur :

`ValueError: the greenlet library is required to use this function. No module named greenlet`

Corrections :

- ajout de `greenlet==3.1.1` dans `requirements.txt` ;
- ajout de `runtime.txt` et `.python-version` pour forcer Python 3.11.9 sur Railway ;
- conservation de la conversion automatique `postgresql://` → `postgresql+asyncpg://`.

Après upload sur Railway, redeploy complet.
