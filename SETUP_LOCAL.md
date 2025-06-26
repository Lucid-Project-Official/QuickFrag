# 🎯 QuickFrag - Configuration Serveur Local

## Solution tout-en-un sur votre serveur cloud

Cette solution lance **bot Discord + serveur Steam callback** sur le même serveur.

---

## 📋 Configuration

### 1. Variables d'environnement

Ajoutez une seule nouvelle variable à vos variables existantes :

```bash
# Variables existantes (vous les avez déjà)
DISCORD_TOKEN=votre_token_discord
SUPABASE_URL=https://votre-projet.supabase.co
SUPABASE_ANON_KEY=votre_cle_anonyme

# ✨ NOUVELLE variable pour les notifications
DISCORD_WEBHOOK_URL=https://discord.com/api/webhooks/YOUR_WEBHOOK
```

### 2. Créer un webhook Discord

1. **Serveur Discord** → **Paramètres** → **Intégrations** → **Webhooks**
2. **Nouveau webhook** → Choisir un canal (ex: #notifications)
3. **Copier l'URL** → L'ajouter dans `DISCORD_WEBHOOK_URL`

### 3. Installation

```bash
# Installer les nouvelles dépendances
pip install flask requests

# Ou via requirements.txt
pip install -r requirements.txt
```

---

## 🚀 Démarrage

### Option A : Lancement automatique (recommandé)
```bash
python start_quickfrag.py
```

### Option B : Lancement manuel
```bash
# Terminal 1 - Bot Discord
python QuickFrag.py

# Terminal 2 - Serveur Steam
python steam_callback_server.py
```

---

## 🌐 Configuration domaine

### Nginx (si vous utilisez un reverse proxy)

Ajoutez à votre configuration Nginx :

```nginx
server {
    server_name quickfrag.io;
    
    # Vos configurations existantes...
    
    # ✨ NOUVEAU - Route pour Steam callback
    location /steam-callback {
        proxy_pass http://localhost:5000/steam-callback;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
    
    location /health {
        proxy_pass http://localhost:5000/health;
        proxy_set_header Host $host;
    }
}
```

### Test sans domaine

Si vous n'avez pas encore configuré le domaine, vous pouvez temporairement modifier `QuickFrag.py` :

```python
# Remplacer temporairement
"openid.return_to": f"http://VOTRE_IP:5000/steam-callback?token={token}&discord_id={discord_user_id}",
"openid.realm": "http://VOTRE_IP:5000",
```

---

## ✅ Vérification

### Services actifs
```bash
# Vérifier que les services tournent
curl http://localhost:5000/health

# Réponse attendue :
# {"status": "healthy", "service": "QuickFrag Steam Callback"}
```

### Test complet
1. **Bot Discord** → Commande join_game
2. **Message reçu** → Lien Steam 
3. **Clic sur lien** → Authentification Steam
4. **Retour sur site** → Page de succès
5. **Discord** → Message de confirmation

---

## 📊 Monitoring

### Logs en temps réel
```bash
# Voir tous les logs
python start_quickfrag.py

# Ou séparément
tail -f discord.log
tail -f steam_server.log
```

### Ports utilisés
- **Port 5000** : Serveur Steam callback
- **Bot Discord** : Pas de port (client)

---

## 🔧 Dépannage

### Problèmes courants

1. **Port 5000 occupé**
   ```bash
   # Changer le port dans steam_callback_server.py
   app.run(host='0.0.0.0', port=5001, debug=False)
   ```

2. **Webhook Discord ne marche pas**
   ```bash
   # Tester le webhook manuellement
   curl -H "Content-Type: application/json" \
        -d '{"content":"Test webhook"}' \
        YOUR_WEBHOOK_URL
   ```

3. **Variables d'environnement**
   ```bash
   # Vérifier qu'elles sont chargées
   python -c "import os; print(os.getenv('DISCORD_TOKEN'))"
   ```

---

## 🎯 Avantages de cette solution

✅ **Tout centralisé** sur votre serveur  
✅ **Mêmes variables d'environnement** que le bot  
✅ **Pas de service externe** (Vercel/Netlify)  
✅ **Ultra simple** à déployer  
✅ **Monitoring facile** - tout au même endroit  

---

## 🆚 Comparaison

| Solution | Simplicité | Contrôle | Coût |
|----------|------------|----------|------|
| **Serveur local** | ⭐⭐⭐ | ⭐⭐⭐ | Gratuit |
| Vercel | ⭐⭐⭐⭐ | ⭐⭐ | Gratuit* |
| VPS séparé | ⭐ | ⭐⭐⭐ | $$$ |

**Recommandation :** Utilisez la solution serveur local ! 🎯 