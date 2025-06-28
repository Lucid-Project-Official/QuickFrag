# 🎯 QuickFrag - Platform Gaming Ultra Moderne

QuickFrag est une plateforme gaming ultra-moderne pour Counter-Strike 2 avec un système de classement ELO avancé, intégration Steam complète et interface futuriste avec modèles 3D interactifs.

## ✨ Fonctionnalités Principales

### 🎮 Système de Jeu
- **Système ELO Ultra-Précis** : Algorithme de classement compétitif avancé
- **Intégration Steam OpenID** : Authentification sécurisée avec Steam
- **Whitelist Dynamique** : Sécurité maximale avec validation automatisée
- **Statistiques en Temps Réel** : Analyse live des performances

### 🚀 Interface Futuriste
- **Design Cyberpunk** : Interface ultra-moderne avec effets néon
- **Modèles 3D Flottants** : Objets CS2 interactifs en WebGL ([model-viewer.dev](https://modelviewer.dev/))
- **Animations Avancées** : Particules, effets parallax et transitions fluides
- **Effets Sonores** : Sons synthétiques pour une expérience immersive

### 🎨 Modèles 3D Intégrés
- **AK-47** : Fusil d'assaut iconique avec animation de rotation
- **Fumigènes** : Grenades tactiques avec effets de particules
- **Couteaux** : Armes de mêlée avec reflets métalliques
- **Casques Tactiques** : Équipements de protection
- **Bombes C4** : Explosifs avec lueur néon

## 🛠 Technologies Utilisées

### Frontend
- **HTML5** avec sémantique moderne
- **CSS3** avec variables CSS, gradients et animations
- **JavaScript ES6+** avec API modernes (Intersection Observer, Web Audio)
- **Google Model Viewer** pour le rendu 3D WebGL
- **Fonts Google** : Orbitron (futuriste) + Rajdhani (moderne)

### Backend
- **Python 3.13+** avec urllib (sans dépendances lourdes)
- **Vercel Functions** pour l'API serverless
- **Supabase** pour la base de données PostgreSQL
- **Discord API** pour l'intégration communautaire

### Modèles 3D
- **Format GLB/GLTF** pour une compatibilité maximale
- **Khronos Group glTF Samples** pour les modèles de référence
- **Sketchfab Integration** pour les assets CS2 ([lien Sketchfab](https://sketchfab.com/search?q=counterstrike&type=models))

## 🚀 Installation Rapide

### 1. Cloner et Installer
```bash
git clone https://github.com/votreuser/quickfrag.git
cd quickfrag
pip install -r requirements.txt
```

### 2. Variables d'Environnement
```bash
export SUPABASE_URL="votre_url_supabase"
export SUPABASE_ANON_KEY="votre_clé_supabase"
export DISCORD_TOKEN="votre_token_discord"
```

### 3. Déploiement Vercel
```bash
npm install -g vercel
vercel --prod
```

## 🎯 Configuration Avancée

### Base de Données (Supabase)
```sql
-- Table Players
CREATE TABLE Players (
    id SERIAL PRIMARY KEY,
    Steam_PlayerID VARCHAR(20) UNIQUE,
    Discord_PlayerID VARCHAR(20) UNIQUE,
    PlayerName VARCHAR(50),
    PlayerRank VARCHAR(20),
    PlayerElo INTEGER DEFAULT 1000
);

-- Table ServersManager
CREATE TABLE ServersManager (
    server_IPAdress VARCHAR(21) PRIMARY KEY,
    match_playersteam_1 VARCHAR(20),
    match_playersteam_2 VARCHAR(20),
    -- ... jusqu'à match_playersteam_10
);
```

### Plugin CS2 (QFWhitelist)
```csharp
// Configuration dans QFWhitelist/
public class QFWhitelistPlugin : BasePlugin
{
    public override string ModuleName => "QFWhitelist";
    // Commandes disponibles :
    // css_qf_reload - Recharge la whitelist
    // css_qf_status - Affiche le statut
    // css_qf_toggle - Active/désactive
}
```

## 🎨 Personnalisation des Modèles 3D

### Ajouter de Nouveaux Modèles
```javascript
// Dans models.json
{
  "cs2_models": {
    "weapons": {
      "nouveaumodele": {
        "name": "Nom du Modèle",
        "url": "https://url-vers-le-modele.glb",
        "scale": "1.0 1.0 1.0",
        "description": "Description du modèle"
      }
    }
  }
}
```

### Créer des Animations Personnalisées
```css
@keyframes votre-animation {
    0% { transform: translateY(0px) rotate(0deg); }
    50% { transform: translateY(-30px) rotate(180deg); }
    100% { transform: translateY(0px) rotate(360deg); }
}

.votre-modele {
    animation: votre-animation 10s ease-in-out infinite;
}
```

## 🎮 Easter Eggs

- **Konami Code** : ↑↑↓↓←→←→BA pour le mode ultra futuriste
- **Effets Sonores** : Sons synthétiques sur les interactions
- **Particules Dynamiques** : 50+ particules animées en arrière-plan

## 📱 Responsive & Performance

- **Mobile First** : Interface adaptative pour tous les écrans
- **WebGL Optimisé** : Rendu 3D performant sur mobile
- **Lazy Loading** : Chargement progressif des modèles 3D
- **PWA Ready** : Installation possible comme application

## 🔧 API Endpoints

### Steam Authentication
```
GET /api/steam-callback
Paramètres : discord_id, token, openid_*
Retour : Page de succès ou erreur
```

### Discord Integration
```javascript
// Envoi automatique de notification Discord
async function send_discord_message(discord_id, steam_id)
```

## 🌟 Fonctionnalités Avancées

### Système ELO
- **Algorithme Précis** : Calcul basé sur les performances
- **Rangs Visuels** : De Silver I à Global Elite
- **Historique** : Suivi des progressions

### Whitelist Intelligente
- **Mise à Jour Automatique** : Rechargement toutes les 10 secondes
- **Multi-Serveurs** : Gestion centralisée
- **Kick Automatique** : Éjection des joueurs non autorisés

### Interface 3D
- **5 Modèles Simultanés** : Animations synchronisées
- **Effets de Lueur** : Halos colorés dynamiques
- **Interactions** : Survol avec effets spéciaux

## 📋 Structure du Projet

```
QuickFrag/
├── index.html              # Page principale ultra-moderne
├── styles.css              # Styles futuristes avec animations
├── script.js               # JavaScript avec effets 3D
├── models.json             # Configuration des modèles 3D CS2
├── api/
│   └── steam-callback.py   # API Vercel pour Steam OpenID
├── QFWhitelist/            # Plugin CS2 renommé
├── Progresql Database/     # Données de configuration
└── vercel.json            # Configuration déploiement
```

## 🎯 Roadmap

- [ ] **Mode VR** : Support des casques de réalité virtuelle
- [ ] **IA Prédictive** : Analyse des tendances de jeu
- [ ] **Blockchain** : NFTs pour les skins rares
- [ ] **Streaming Integration** : Support Twitch/YouTube
- [ ] **Tournament Mode** : Système de tournois automatisés

## 🚀 Déploiement Production

1. **Configuration Vercel** :
   ```bash
   vercel env add SUPABASE_URL
   vercel env add SUPABASE_ANON_KEY
   vercel env add DISCORD_TOKEN
   ```

2. **Deploy** :
   ```bash
   vercel --prod
   ```

3. **URL Live** : `https://quickfrag.vercel.app`

## 📄 Licence

MIT License - Libre d'utilisation pour projets open source

---

🚀 **Créé par l'équipe QuickFrag** - *"Gaming Evolution Starts Here"*

⚡ **Site Ultra Moderne** avec modèles 3D CS2 flottants et interface cyberpunk 