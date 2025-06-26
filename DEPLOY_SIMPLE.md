# 🚀 Déploiement Ultra Simple QuickFrag.io

## Solution Vercel (5 minutes ⏱️)

### 1. Prérequis
- Compte GitHub 
- Compte Vercel (gratuit)
- Compte Discord avec webhook

### 2. Préparation
```bash
# Créer un nouveau repo GitHub avec ces fichiers :
# - api/steam-callback.py
# - vercel.json  
# - requirements.txt
```

### 3. Déploiement Vercel

1. **Aller sur [vercel.com](https://vercel.com)**
2. **Se connecter avec GitHub**
3. **Import Project** → Sélectionner votre repo
4. **Deploy** (automatique)

### 4. Configuration variables d'environnement

Dans le dashboard Vercel → **Settings** → **Environment Variables** :

```
SUPABASE_URL = https://votre-projet.supabase.co
SUPABASE_ANON_KEY = votre_cle_anonyme
DISCORD_WEBHOOK_URL = https://discord.com/api/webhooks/...
```

### 5. Créer un webhook Discord

1. **Serveur Discord** → **Paramètres** → **Intégrations** → **Webhooks**
2. **Créer un webhook**
3. **Copier l'URL** → Mettre dans `DISCORD_WEBHOOK_URL`

### 6. Configurer le domaine (optionnel)

Dans Vercel → **Domains** :
- Ajouter `quickfrag.io`
- Ou utiliser l'URL Vercel : `https://quickfrag.vercel.app`

### 7. Mettre à jour le bot Discord

Dans `QuickFrag.py`, vérifier que l'URL est correcte :
```python
"openid.return_to": f"https://quickfrag.vercel.app/api/steam-callback?token={token}&discord_id={discord_user_id}",
```

---

## ✅ C'est tout !

**URL finale** : `https://quickfrag.vercel.app/api/steam-callback`

**Test** : Redémarrer le bot Discord et tester la liaison Steam

---

## 🔧 Alternative : Solution PHP (encore plus simple)

Si vous préférez PHP :

**fichier `steam-callback.php` :**
```php
<?php
// Récupération des paramètres
$steam_id = null;
if (isset($_GET['openid_identity'])) {
    if (preg_match('/steamcommunity\.com\/openid\/id\/(\d+)/', $_GET['openid_identity'], $matches)) {
        $steam_id = $matches[1];
    }
}

$discord_id = $_GET['discord_id'] ?? null;

if ($steam_id && $discord_id) {
    // Mettre à jour Supabase via cURL
    // Envoyer webhook Discord via cURL
    echo "✅ Compte lié avec succès !";
} else {
    echo "❌ Erreur lors de la liaison";
}
?>
```

**Déployer sur n'importe quel hébergeur PHP** (OVH, 1&1, etc.)

---

## 🎯 Résumé

**Plus simple** = Vercel + Fonction Python (5 min de déploiement)
**Plus basique** = PHP sur hébergeur mutualisé 
**Plus robuste** = Solution Flask complète (si besoin plus tard) 