# 🎯 QuickFrag - Déploiement Ultra Simple (Systemd + Vercel)

## Solution : Vercel (sans Flask) + Service Systemd existant

**Avantages :**
- ✅ **Pas de Flask** - Utilise seulement Python stdlib  
- ✅ **Zéro dépendance** - Fonction Vercel pure
- ✅ **Service systemd intact** - Garde votre bot Discord tel quel
- ✅ **Variables partagées** - Même principe que votre service actuel

---

## 🚀 Déploiement Vercel (2 minutes)

### 1. Créer un repo GitHub

```bash
# Créer un dossier avec ces 3 fichiers :
quickfrag-steam/
├── api/steam-callback.py
├── vercel.json
└── requirements.txt
```

### 2. Déployer sur Vercel

1. **[vercel.com](https://vercel.com)** → **New Project**
2. **Import** votre repo GitHub  
3. **Deploy** (automatique)

### 3. Configurer les variables Vercel

Dans **Vercel Dashboard** → **Settings** → **Environment Variables** :

```bash
# Copier EXACTEMENT les mêmes valeurs de votre service systemd
SUPABASE_URL = https://votre-projet.supabase.co
SUPABASE_ANON_KEY = votre_cle_anonyme
DISCORD_WEBHOOK_URL = https://discord.com/api/webhooks/NOUVEAU_WEBHOOK
```

---

## 🔧 Modification du service systemd

### Ajouter UNE SEULE variable

Éditer `/etc/systemd/system/cs2_python_script.service` :

```ini
[Unit]
Description=CS2 Python Script
After=network.target

[Service]
Type=simple
User=votre_user
WorkingDirectory=/path/to/your/script
ExecStart=/usr/bin/python3.13 QuickFrag.py

# Variables existantes (gardez-les telles quelles)
Environment=DISCORD_TOKEN=votre_token
Environment=SUPABASE_URL=https://votre-projet.supabase.co
Environment=SUPABASE_ANON_KEY=votre_cle_anonyme

# ✨ NOUVELLE variable pour le webhook Discord
Environment=DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/NOUVEAU_WEBHOOK

Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### Redémarrer le service

```bash
sudo systemctl daemon-reload
sudo systemctl restart cs2_python_script
```

---

## 🎮 Créer le webhook Discord

1. **Serveur Discord** → **Paramètres serveur** → **Intégrations**
2. **Créer un webhook** → Choisir canal (ex: #notifications)  
3. **Copier l'URL** → Utiliser dans les deux endroits :
   - Service systemd
   - Variables Vercel

---

## ✅ Test final

1. **Redémarrer le bot** : `sudo systemctl restart cs2_python_script`
2. **Tester join_game** sur Discord
3. **Cliquer sur lien Steam** → Doit aller sur Vercel
4. **Authentification Steam** → Page de succès
5. **Notification Discord** → Message de confirmation

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