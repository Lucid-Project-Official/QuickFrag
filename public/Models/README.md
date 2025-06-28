# 🎯 Modèles 3D QuickFrag

Ce dossier contient les modèles 3D (.glb) utilisés sur la page de confirmation de connexion Steam.

## 📁 Structure des fichiers

Les modèles suivants sont utilisés :

- ✅ `ak47-redline.glb` - AK-47 | Redline (2.4MB)
- ❌ `m4a4-asiimov.glb` - M4A4 | Asiimov (manquant)
- ❌ `p90-asiimov.glb` - P90 | Asiimov (manquant)  
- ❌ `karambit-fade.glb` - Karambit | Fade (manquant)

## 🔧 Comment ajouter un modèle

1. **Télécharge** ton modèle .glb depuis Sketchfab ou autre source
2. **Renomme** le fichier selon le nom exact attendu
3. **Place** le fichier dans ce dossier `public/Models/`
4. **Deploy** sur Vercel - le modèle sera automatiquement accessible

## 🌐 URLs d'accès

Les modèles sont accessibles via :
```
https://ton-domaine.vercel.app/Models/nom-du-fichier.glb
```

## ⚙️ Configuration

Le fichier `vercel.json` est configuré pour :
- ✅ Servir les fichiers .glb avec le bon type MIME
- ✅ Activer CORS pour model-viewer
- ✅ Cache optimisé (1 an)
- ✅ Headers de sécurité

## 🎮 Modèles recommandés

Pour CS2, privilégier :
- **Armes** : AK-47, M4A4, AWP, P90
- **Skins** : Asiimov, Redline, Dragon Lore, Fade
- **Accessoires** : Couteaux, grenades, C4

## 📏 Optimisation

- **Taille max** : 5MB par fichier
- **Format** : GLB uniquement (pas GLTF)
- **Textures** : Intégrées dans le GLB
- **Polygones** : < 50k pour de bonnes performances 