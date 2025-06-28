# 🎯 QuickFrag Steam Callback - Vercel Function

Fonction serverless pour gérer l'authentification Steam OpenID dans QuickFrag.

## 📋 Structure

```
├── api/
│   └── steam-callback.py    # Fonction Vercel pour Steam OpenID
├── vercel.json              # Configuration Vercel
├── requirements.txt         # Dépendances Python (vide - stdlib only)
└── DEPLOY_SYSTEMD.md        # Guide de déploiement
```

## 🚀 Déploiement

1. **Cloner ce repo**
2. **Configurer les variables d'environnement sur Vercel** :
   - `DISCORD_TOKEN`
   - `SUPABASE_URL` 
   - `SUPABASE_ANON_KEY`
3. **Déployer** : `vercel --prod`

## 🔗 URL

```
https://quickfrag.vercel.app/api/steam-callback
```

## 📖 Documentation

Voir `DEPLOY_SYSTEMD.md` pour le guide complet de déploiement.

---

**⚡ Fonction ultra-légère** : Utilise uniquement Python stdlib (urllib, json, re) 