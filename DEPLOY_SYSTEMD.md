# 🚀 Déploiement QuickFrag avec Vercel (Solution sans Flask)

## 📋 Prérequis
- Compte Vercel
- Bot Discord déjà fonctionnel avec service systemd
- Variables d'environnement configurées dans systemd

## 🔧 Configuration des variables d'environnement

### Dans votre service systemd `/etc/systemd/system/cs2_python_script.service`

**AUCUNE variable supplémentaire à ajouter !** Le système utilise maintenant directement le token de votre bot Discord.

Vos variables existantes suffisent :
```ini
Environment="DISCORD_TOKEN=votre_token_discord"
Environment="SUPABASE_URL=https://xxxxx.supabase.co"
Environment="SUPABASE_ANON_KEY=votre_clé_anon"
```

## 🌐 Déploiement Vercel

### 1. Cloner le projet sur votre machine
```bash
git clone https://github.com/votre-username/quickfrag.git
cd quickfrag
```

### 2. Installer Vercel CLI
```bash
npm install -g vercel
```

### 3. Se connecter à Vercel
```bash
vercel login
```

### 4. Déployer le projet
```bash
vercel
```

Lors du déploiement, Vercel vous demandera :
- **Project name**: `quickfrag`
- **Directory**: Appuyez sur Entrée (racine du projet)
- **Settings correct**: `y`

### 5. Configurer les variables d'environnement sur Vercel

Aller sur [vercel.com/dashboard](https://vercel.com/dashboard), sélectionner votre projet, puis :
- **Settings** → **Environment Variables**
- Ajouter les mêmes variables que votre service systemd :

```
DISCORD_TOKEN = votre_token_discord
SUPABASE_URL = https://xxxxx.supabase.co  
SUPABASE_ANON_KEY = votre_clé_anon
```

## ✅ Vérification

Votre fonction sera disponible à l'adresse :
```
https://quickfrag.vercel.app/api/steam-callback
```

## 🔄 Mise à jour du code bot

Dans `QuickFrag.py`, vérifiez que l'URL pointe vers Vercel :
```python
"openid.return_to": f"https://quickfrag.vercel.app/api/steam-callback?token={token}&discord_id={discord_user_id}",
```

## 🎯 Fonctionnement

1. Utilisateur clique sur le lien Steam dans Discord
2. Steam redirige vers `https://quickfrag.vercel.app/api/steam-callback`
3. Vercel vérifie l'authentification Steam
4. Met à jour Supabase avec le Steam ID
5. **Envoie directement un message privé Discord à l'utilisateur via l'API Discord**
6. Utilisateur reçoit la confirmation

## 🛠️ Redémarrage du service

Si vous modifiez des variables :
```bash
sudo systemctl daemon-reload
sudo systemctl restart cs2_python_script.service
```

## 📝 Avantages de cette solution

- ✅ **Ultra simple** : Pas de Flask, juste stdlib Python
- ✅ **Serverless** : Vercel gère tout automatiquement  
- ✅ **Gratuit** : Dans les limites Vercel
- ✅ **Léger** : Aucune dépendance supplémentaire
- ✅ **Direct** : Utilise directement le token du bot Discord
- ✅ **Rapide** : Fonction lambda très performante

---

## 🎯 Architecture finale

```
Votre Serveur                     Vercel (Externe)
├── QuickFrag.py (Bot)     ←→     api/steam-callback.py
├── Service systemd               (Fonction serverless)
└── Variables d'env       ←→     Variables Vercel
```

**URL finale :** `https://quickfrag.vercel.app/api/steam-callback`

---

## 🔄 Avantages de cette solution

✅ **Bot Discord** reste sur votre serveur (contrôle total)  
✅ **Steam callback** sur Vercel (zéro maintenance)  
✅ **Pas de Flask** - Python stdlib uniquement  
✅ **Service systemd intact** - Une seule variable ajoutée  
✅ **Gratuit** - Vercel free tier largement suffisant  

---

## 🚨 Si vous voulez utiliser votre domaine

Dans Vercel → **Domains** → Ajouter `quickfrag.io`

Puis modifier `QuickFrag.py` :
```python
"openid.return_to": f"https://quickfrag.io/api/steam-callback?token={token}&discord_id={discord_user_id}",
"openid.realm": "https://quickfrag.io",
```

---

## 🎉 C'est tout !

**Manipulation minimale :** 
1. Deploy sur Vercel (2 clics)
2. Ajouter 1 variable au service systemd  
3. Redémarrer le service

**Plus simple impossible !** 🚀 