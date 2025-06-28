"""
🎯 QuickFrag Steam Callback - Vercel Function Ultra Simple
Compatible Python 3.13.2 - Pas de Flask !
"""

import json
import re
import os
import urllib.parse
import urllib.request
from http.server import BaseHTTPRequestHandler

def verify_steam_openid(params):
    """Vérifie Steam OpenID avec urllib uniquement"""
    try:
        verify_params = dict(params)
        verify_params["openid.mode"] = "check_authentication"
        
        data = urllib.parse.urlencode(verify_params).encode('utf-8')
        req = urllib.request.Request("https://steamcommunity.com/openid/login", data=data)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            result = response.read().decode('utf-8')
            
            if "is_valid:true" in result:
                identity_url = params.get("openid.identity", "")
                match = re.search(r'steamcommunity\.com/openid/id/(\d+)', identity_url)
                return match.group(1) if match else None
        
        return None
    except Exception as e:
        print(f"Erreur Steam: {e}")
        return None

def update_supabase(steam_id, discord_id):
    """Met à jour Supabase avec urllib seulement"""
    try:
        supabase_url = os.environ.get("SUPABASE_URL")
        supabase_key = os.environ.get("SUPABASE_ANON_KEY")
        
        if not supabase_url or not supabase_key:
            return False
        
        # Vérifier si Steam ID existe déjà
        check_url = f"{supabase_url}/rest/v1/Players?Steam_PlayerID=eq.{steam_id}&select=Discord_PlayerID"
        headers = {
            "apikey": supabase_key,
            "Authorization": f"Bearer {supabase_key}",
            "Content-Type": "application/json"
        }
        
        req = urllib.request.Request(check_url)
        for key, value in headers.items():
            req.add_header(key, value)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            existing = json.loads(response.read().decode('utf-8'))
            
        if existing:
            return False  # Steam ID déjà utilisé
        
        # Vérifier si Discord ID existe
        user_url = f"{supabase_url}/rest/v1/Players?Discord_PlayerID=eq.{discord_id}&select=*"
        req = urllib.request.Request(user_url)
        for key, value in headers.items():
            req.add_header(key, value)
        
        with urllib.request.urlopen(req, timeout=10) as response:
            user_data = json.loads(response.read().decode('utf-8'))
        
        # Données à insérer/mettre à jour
        data = {
            "Steam_PlayerID": steam_id,
            "Discord_PlayerID": discord_id,
            "PlayerName": f"User_{discord_id}",
            "PlayerRank": "SilverOne",
            "PlayerElo": 1000
        }
        
        if user_data:
            # Mettre à jour
            update_url = f"{supabase_url}/rest/v1/Players?Discord_PlayerID=eq.{discord_id}"
            req = urllib.request.Request(update_url, method="PATCH")
        else:
            # Créer nouveau
            update_url = f"{supabase_url}/rest/v1/Players"
            req = urllib.request.Request(update_url, method="POST")
        
        for key, value in headers.items():
            req.add_header(key, value)
        req.add_header("Prefer", "return=minimal")
        
        json_data = json.dumps(data).encode('utf-8')
        req.data = json_data
        
        urllib.request.urlopen(req, timeout=10)
        return True
        
    except Exception as e:
        print(f"Erreur Supabase: {e}")
        return False

def send_discord_message(discord_id, steam_id):
    """Envoie message Discord direct avec l'API Discord"""
    try:
        discord_token = os.environ.get("DISCORD_TOKEN")
        if not discord_token:
            print("Token Discord manquant")
            return
        
        # Créer le DM avec l'utilisateur
        create_dm_url = "https://discord.com/api/v10/users/@me/channels"
        dm_data = {
            "recipient_id": discord_id
        }
        
        # Headers Discord API
        headers = {
            "Authorization": f"Bot {discord_token}",
            "Content-Type": "application/json"
        }
        
        # Créer le DM
        dm_req = urllib.request.Request(create_dm_url)
        for key, value in headers.items():
            dm_req.add_header(key, value)
        dm_req.data = json.dumps(dm_data).encode('utf-8')
        
        with urllib.request.urlopen(dm_req, timeout=10) as response:
            dm_result = json.loads(response.read().decode('utf-8'))
            channel_id = dm_result.get("id")
        
        if not channel_id:
            print("Impossible de créer le DM")
            return
        
        # Envoyer le message
        message_url = f"https://discord.com/api/v10/channels/{channel_id}/messages"
        
        embed = {
            "title": "✅ Compte Steam lié avec succès !",
            "description": f"Votre compte Steam a été lié à votre compte Discord.\n\n**Steam ID**: {steam_id}\n**Rang initial**: Silver I\n**ELO initial**: 1000",
            "color": 3066993
        }
        
        message_data = {
            "embeds": [embed]
        }
        
        msg_req = urllib.request.Request(message_url)
        for key, value in headers.items():
            msg_req.add_header(key, value)
        msg_req.data = json.dumps(message_data).encode('utf-8')
        
        urllib.request.urlopen(msg_req, timeout=10)
        print(f"Message Discord envoyé à {discord_id}")
        
    except Exception as e:
        print(f"Erreur Discord API: {e}")

class handler(BaseHTTPRequestHandler):
    """Handler Vercel ultra simple"""
    
    def do_GET(self):
        try:
            # Parser l'URL
            url_parts = urllib.parse.urlparse(self.path)
            params = urllib.parse.parse_qs(url_parts.query)
            
            # Convertir les listes en valeurs simples
            flat_params = {k: v[0] if v else "" for k, v in params.items()}
            
            # Récupérer les paramètres requis
            discord_id = flat_params.get('discord_id')
            token = flat_params.get('token')
            
            if not discord_id or not token:
                self.send_error(400, "Paramètres manquants")
                return
            
            # Vérifier Steam
            steam_id = verify_steam_openid(flat_params)
            if not steam_id:
                self.send_error(400, "Vérification Steam échouée")
                return
            
            # Mettre à jour base de données
            if not update_supabase(steam_id, discord_id):
                self.send_error(400, "Steam ID déjà lié ou erreur base de données")
                return
            
            # Envoyer notification
            send_discord_message(discord_id, steam_id)
            
            # Page de succès
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = f"""
            <!DOCTYPE html>
            <html lang="fr">
            <head>
                <title>QuickFrag - Compte Lié</title>
                <meta charset="utf-8">
                                 <meta name="viewport" content="width=device-width, initial-scale=1.0">
                 <script type="module" src="https://ajax.googleapis.com/ajax/libs/model-viewer/3.4.0/model-viewer.min.js"></script>
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
                    
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                                         body {{
                         font-family: 'Orbitron', monospace;
                         background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e  50%, #0f3460 75%, #003366 100%);
                         min-height: 100vh;
                         overflow-x: hidden;
                         position: relative;
                         color: #ffffff;
                         opacity: 0;
                         animation: pageEntrance 2s ease-out forwards;
                     }}
                    
                    .stars {{
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        pointer-events: none;
                        z-index: 1;
                    }}
                    
                    .star {{
                        position: absolute;
                        width: 2px;
                        height: 2px;
                        background: #ffffff;
                        border-radius: 50%;
                        animation: twinkle 3s infinite alternate;
                    }}
                    
                                         @keyframes twinkle {{
                         0% {{ opacity: 0.3; }}
                         100% {{ opacity: 1; }}
                     }}
                     
                     @keyframes pageEntrance {{
                         0% {{ 
                             opacity: 0;
                             transform: scale(0.8);
                             filter: blur(20px);
                         }}
                         50% {{
                             opacity: 0.7;
                             transform: scale(1.05);
                             filter: blur(5px);
                         }}
                         100% {{ 
                             opacity: 1;
                             transform: scale(1);
                             filter: blur(0);
                         }}
                     }}
                     
                     @keyframes slideInFromTop {{
                         0% {{
                             opacity: 0;
                             transform: translateY(-100px) rotateX(-90deg);
                         }}
                         100% {{
                             opacity: 1;
                             transform: translateY(0) rotateX(0);
                         }}
                     }}
                     
                     @keyframes slideInFromBottom {{
                         0% {{
                             opacity: 0;
                             transform: translateY(100px) scale(0.5);
                         }}
                         100% {{
                             opacity: 1;
                             transform: translateY(0) scale(1);
                         }}
                     }}
                     
                     @keyframes slideInFromLeft {{
                         0% {{
                             opacity: 0;
                             transform: translateX(-200px) rotateY(-45deg);
                         }}
                         100% {{
                             opacity: 1;
                             transform: translateX(0) rotateY(0);
                         }}
                     }}
                     
                     @keyframes slideInFromRight {{
                         0% {{
                             opacity: 0;
                             transform: translateX(200px) rotateY(45deg);
                         }}
                         100% {{
                             opacity: 1;
                             transform: translateX(0) rotateY(0);
                         }}
                     }}
                     
                     @keyframes matrixEntrance {{
                         0% {{
                             opacity: 0;
                             transform: scale(0) rotate(180deg);
                             filter: hue-rotate(180deg) brightness(3);
                         }}
                         50% {{
                             opacity: 0.8;
                             transform: scale(1.2) rotate(0deg);
                             filter: hue-rotate(90deg) brightness(2);
                         }}
                         100% {{
                             opacity: 1;
                             transform: scale(1) rotate(0deg);
                             filter: hue-rotate(0deg) brightness(1);
                         }}
                     }}
                    
                    .main-container {{
                        position: relative;
                        z-index: 10;
                        display: flex;
                        flex-direction: column;
                        align-items: center;
                        justify-content: center;
                        min-height: 100vh;
                        padding: 20px;
                    }}
                    
                                         .success-card {{
                         background: rgba(255, 255, 255, 0.05);
                         backdrop-filter: blur(20px);
                         border: 1px solid rgba(0, 255, 255, 0.3);
                         border-radius: 20px;
                         padding: 40px;
                         max-width: 600px;
                         width: 100%;
                         box-shadow: 
                             0 8px 32px rgba(0, 255, 255, 0.1),
                             inset 0 1px 0 rgba(255, 255, 255, 0.1);
                         position: relative;
                         opacity: 0;
                         animation: slideInFromBottom 1.5s ease-out 0.5s forwards,
                                   cardGlow 2s ease-in-out 2s infinite alternate;
                     }}
                    
                    @keyframes cardGlow {{
                        0% {{ box-shadow: 0 8px 32px rgba(0, 255, 255, 0.1), inset 0 1px 0 rgba(255, 255, 255, 0.1); }}
                        100% {{ box-shadow: 0 8px 32px rgba(0, 255, 255, 0.3), inset 0 1px 0 rgba(255, 255, 255, 0.2); }}
                    }}
                    
                                         .success-title {{
                         font-size: 2.5rem;
                         font-weight: 900;
                         color: #00ffff;
                         margin-bottom: 20px;
                         text-align: center;
                         text-shadow: 0 0 20px rgba(0, 255, 255, 0.5);
                         opacity: 0;
                         animation: slideInFromTop 1.2s ease-out 1s forwards,
                                   titlePulse 2s ease-in-out 2.5s infinite alternate;
                     }}
                    
                    @keyframes titlePulse {{
                        0% {{ text-shadow: 0 0 20px rgba(0, 255, 255, 0.5); }}
                        100% {{ text-shadow: 0 0 30px rgba(0, 255, 255, 0.8); }}
                    }}
                    
                                         .success-subtitle {{
                         font-size: 1.2rem;
                         color: #ffffff;
                         margin-bottom: 30px;
                         text-align: center;
                         opacity: 0;
                         animation: slideInFromTop 1.2s ease-out 1.3s forwards;
                     }}
                     
                     .steam-info {{
                         background: rgba(0, 255, 255, 0.1);
                         border: 1px solid rgba(0, 255, 255, 0.3);
                         border-radius: 10px;
                         padding: 20px;
                         margin: 20px 0;
                         text-align: center;
                         opacity: 0;
                         animation: matrixEntrance 1.5s ease-out 1.8s forwards;
                     }}
                     
                     .success-card p {{
                         opacity: 0;
                         animation: slideInFromBottom 1s ease-out 2.2s forwards;
                     }}
                    
                    .steam-id {{
                        font-size: 1.5rem;
                        font-weight: 700;
                        color: #00ffff;
                        margin-bottom: 10px;
                    }}
                    
                    .discord-info {{
                        color: #7289da;
                        font-size: 1.1rem;
                    }}
                    
                    .floating-model {{
                        position: fixed;
                        pointer-events: none;
                        z-index: 5;
                    }}
                    
                                         .model-ak47 {{
                         top: 20%;
                         right: 10%;
                         width: 200px;
                         height: 200px;
                         opacity: 0;
                         animation: slideInFromRight 2s ease-out 2s forwards,
                                   floatAK 15s linear 4s infinite;
                     }}
                     
                     .model-smoke {{
                         top: 60%;
                         left: 5%;
                         width: 150px;
                         height: 150px;
                         opacity: 0;
                         animation: slideInFromLeft 2s ease-out 2.5s forwards,
                                   floatSmoke 20s linear 4.5s infinite;
                     }}
                     
                     .model-bomb {{
                         top: 30%;
                         left: 15%;
                         width: 120px;
                         height: 120px;
                         opacity: 0;
                         animation: matrixEntrance 2.5s ease-out 3s forwards,
                                   floatBomb 18s linear 5.5s infinite;
                     }}
                     
                     .model-knife {{
                         top: 70%;
                         right: 20%;
                         width: 100px;
                         height: 100px;
                         opacity: 0;
                         animation: slideInFromBottom 2s ease-out 3.5s forwards,
                                   floatKnife 12s linear 5.5s infinite;
                     }}
                    
                    @keyframes floatAK {{
                        0% {{ transform: translateY(0px) rotate(0deg); }}
                        25% {{ transform: translateY(-20px) rotate(90deg); }}
                        50% {{ transform: translateY(0px) rotate(180deg); }}
                        75% {{ transform: translateY(-15px) rotate(270deg); }}
                        100% {{ transform: translateY(0px) rotate(360deg); }}
                    }}
                    
                    @keyframes floatSmoke {{
                        0% {{ transform: translateX(0px) translateY(0px) rotate(0deg); }}
                        25% {{ transform: translateX(30px) translateY(-25px) rotate(90deg); }}
                        50% {{ transform: translateX(0px) translateY(-10px) rotate(180deg); }}
                        75% {{ transform: translateX(-25px) translateY(-20px) rotate(270deg); }}
                        100% {{ transform: translateX(0px) translateY(0px) rotate(360deg); }}
                    }}
                    
                    @keyframes floatBomb {{
                        0% {{ transform: scale(1) rotate(0deg); }}
                        25% {{ transform: scale(1.1) rotate(90deg); }}
                        50% {{ transform: scale(0.9) rotate(180deg); }}
                        75% {{ transform: scale(1.05) rotate(270deg); }}
                        100% {{ transform: scale(1) rotate(360deg); }}
                    }}
                    
                    @keyframes floatKnife {{
                        0% {{ transform: translateY(0px) rotate(0deg) scale(1); }}
                        33% {{ transform: translateY(-30px) rotate(120deg) scale(1.2); }}
                        66% {{ transform: translateY(10px) rotate(240deg) scale(0.8); }}
                        100% {{ transform: translateY(0px) rotate(360deg) scale(1); }}
                    }}
                    
                                         model-viewer {{
                         width: 100%;
                         height: 100%;
                         border-radius: 15px;
                         box-shadow: 0 0 30px rgba(0, 255, 255, 0.4);
                         --poster-color: transparent;
                         --progress-bar-color: #00ffff;
                         --progress-mask: rgba(0, 255, 255, 0.3);
                         filter: drop-shadow(0 0 20px rgba(0, 255, 255, 0.2));
                     }}
                    
                                         .close-button {{
                         margin-top: 30px;
                         padding: 15px 30px;
                         background: linear-gradient(45deg, #00ffff, #0099cc);
                         border: none;
                         border-radius: 50px;
                         color: #000;
                         font-family: 'Orbitron', monospace;
                         font-weight: 700;
                         font-size: 1.1rem;
                         cursor: pointer;
                         transition: all 0.3s ease;
                         box-shadow: 0 4px 15px rgba(0, 255, 255, 0.3);
                         opacity: 0;
                         animation: slideInFromBottom 1.2s ease-out 2.5s forwards;
                     }}
                     
                     .close-button:hover {{
                         transform: translateY(-2px) scale(1.05);
                         box-shadow: 0 8px 25px rgba(0, 255, 255, 0.7);
                         background: linear-gradient(45deg, #00ffff, #ff6b6b);
                     }}
                    
                    @media (max-width: 768px) {{
                        .floating-model {{
                            display: none;
                        }}
                        .success-title {{
                            font-size: 2rem;
                        }}
                        .success-card {{
                            padding: 20px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="stars"></div>
                
                                 <!-- Modèles 3D flottants -->
                 <div class="floating-model model-ak47">
                     <model-viewer
                         src="http://localhost:8080/api/Models/m4a4-asiimov.glb"
                         alt="M4A4 Asiimov"
                         auto-rotate
                         rotation-per-second="30deg"
                         camera-controls
                         disable-zoom
                         disable-pan
                         loading="eager">
                     </model-viewer>
                 </div>
                 
                 <div class="floating-model model-smoke">
                     <model-viewer
                         src="http://localhost:8080/api/Models/p90-asiimov.glb"
                         alt="P90 Asiimov"
                         auto-rotate
                         rotation-per-second="45deg"
                         camera-controls
                         disable-zoom
                         disable-pan
                         loading="eager">
                     </model-viewer>
                 </div>
                 
                 <div class="floating-model model-bomb">
                     <model-viewer
                         src="http://localhost:8080/api/Models/ak47-redline.glb"
                         alt="AK-47 Redline"
                         auto-rotate
                         rotation-per-second="60deg"
                         camera-controls
                         disable-zoom
                         disable-pan
                         loading="eager">
                     </model-viewer>
                 </div>
                 
                 <div class="floating-model model-knife">
                     <model-viewer
                         src="http://localhost:8080/api/Models/karambit-fade.glb"
                         alt="Karambit Fade"
                         auto-rotate
                         rotation-per-second="90deg"
                         camera-controls
                         disable-zoom
                         disable-pan
                         loading="eager">
                     </model-viewer>
                 </div>
                
                <div class="main-container">
                    <div class="success-card">
                        <h1 class="success-title">⚡ CONNEXION ÉTABLIE ⚡</h1>
                        <p class="success-subtitle">Synchronisation Steam ↔ Discord complétée</p>
                        
                                                 <div class="steam-info">
                             <div class="steam-id">Steam ID: {steam_id}</div>
                             <div class="discord-info">🎮 Prêt pour QuickFrag</div>
                         </div>
                         
                         <p style="margin: 20px 0; opacity: 0.8;">
                             ✅ Profil Discord mis à jour<br>
                             ✅ Accès aux serveurs activé<br>
                             ✅ Système de rang initialisé<br>
                             ✅ ELO de départ: 1000 points
                         </p>
                        
                                                 <button class="close-button" onclick="closeWindow()">
                             FERMER LA FENÊTRE
                         </button>
                    </div>
                </div>
                
                                 <script>
                     // Génération des étoiles
                     function createStars() {{
                         const starsContainer = document.querySelector('.stars');
                         const starCount = 100;
                         
                         for (let i = 0; i < starCount; i++) {{
                             const star = document.createElement('div');
                             star.className = 'star';
                             star.style.left = Math.random() * 100 + '%';
                             star.style.top = Math.random() * 100 + '%';
                             star.style.animationDelay = Math.random() * 3 + 's';
                             starsContainer.appendChild(star);
                         }}
                     }}
                     
                     // Fonction de fermeture améliorée
                     function closeWindow() {{
                         // Essayer plusieurs méthodes de fermeture
                         if (window.opener) {{
                             window.close();
                         }} else {{
                             // Fallback : rediriger vers une page vide ou afficher un message
                             if (confirm('Fermer cet onglet ?')) {{
                                 window.open('', '_self').close();
                             }}
                         }}
                     }}
                     
                     // Gestion des animations d'entrée et modèles 3D
                     document.addEventListener('DOMContentLoaded', function() {{
                         // Créer les étoiles avec délai
                         setTimeout(createStars, 500);
                         
                         // Audio feedback (optionnel)
                         const playEntranceSound = () => {{
                             try {{
                                 const audioContext = new (window.AudioContext || window.webkitAudioContext)();
                                 const oscillator = audioContext.createOscillator();
                                 const gainNode = audioContext.createGain();
                                 
                                 oscillator.connect(gainNode);
                                 gainNode.connect(audioContext.destination);
                                 
                                 oscillator.frequency.setValueAtTime(220, audioContext.currentTime);
                                 oscillator.frequency.exponentialRampToValueAtTime(440, audioContext.currentTime + 0.5);
                                 
                                 gainNode.gain.setValueAtTime(0.1, audioContext.currentTime);
                                 gainNode.gain.exponentialRampToValueAtTime(0.01, audioContext.currentTime + 0.5);
                                 
                                 oscillator.start(audioContext.currentTime);
                                 oscillator.stop(audioContext.currentTime + 0.5);
                             }} catch(e) {{
                                 console.log('Audio non supporté');
                             }}
                         }};
                         
                         // Déclencher le son d'entrée après 1 seconde
                         setTimeout(playEntranceSound, 1000);
                         
                         // Gestion des modèles 3D avec effects d'entrée
                         const models = document.querySelectorAll('model-viewer');
                         models.forEach((model, index) => {{
                             // Gestion du chargement
                             model.addEventListener('load', function() {{
                                 console.log('Modèle 3D chargé:', this.alt);
                                 // Ajouter un effet de lueur supplémentaire quand le modèle est chargé
                                 this.style.filter = 'drop-shadow(0 0 25px rgba(0, 255, 255, 0.5))';
                                 
                                 // Effet de particules au chargement
                                 this.style.animation += ', matrixEntrance 0.5s ease-out';
                             }});
                             
                             // Gestion d'erreur avec diagnostic détaillé
                             model.addEventListener('error', function() {{
                                 console.error('❌ Modèle 3D non chargé:', this.alt);
                                 console.error('   - Chemin:', this.src);
                                 console.error('   - Vérifiez que le fichier existe dans le dossier api/Models/');
                                 
                                 // Remplacer par un modèle de fallback
                                 this.src = 'https://modelviewer.dev/shared-assets/models/Astronaut.glb';
                                 this.style.filter = 'grayscale(100%) opacity(0.5)';
                                 
                                 // Afficher un message d'erreur visible
                                 const errorMsg = document.createElement('div');
                                 errorMsg.style.cssText = `
                                     position: absolute;
                                     top: 50%;
                                     left: 50%;
                                     transform: translate(-50%, -50%);
                                     background: rgba(255, 0, 0, 0.8);
                                     color: white;
                                     padding: 5px 10px;
                                     border-radius: 5px;
                                     font-size: 12px;
                                     z-index: 1000;
                                 `;
                                 errorMsg.textContent = `❌ ${{this.alt}} manquant`;
                                 this.parentElement.style.position = 'relative';
                                 this.parentElement.appendChild(errorMsg);
                             }});
                             
                             // Animation de lueur progressive au survol
                             model.addEventListener('mouseenter', function() {{
                                 this.style.transform = 'scale(1.1)';
                                 this.style.filter = 'drop-shadow(0 0 40px rgba(0, 255, 255, 0.8))';
                                 this.style.transition = 'all 0.3s ease';
                             }});
                             
                             model.addEventListener('mouseleave', function() {{
                                 this.style.transform = 'scale(1)';
                                 this.style.filter = 'drop-shadow(0 0 25px rgba(0, 255, 255, 0.2))';
                             }});
                         }});
                         
                         // Effet de scan de ligne futuriste
                         const createScanLine = () => {{
                             const scanLine = document.createElement('div');
                             scanLine.style.cssText = `
                                 position: fixed;
                                 top: 0;
                                 left: 0;
                                 width: 100%;
                                 height: 2px;
                                 background: linear-gradient(90deg, transparent, #00ffff, transparent);
                                 z-index: 9999;
                                 animation: scanDown 3s ease-out;
                             `;
                             document.body.appendChild(scanLine);
                             setTimeout(() => scanLine.remove(), 3000);
                         }};
                         
                         // Ajouter le style de scan
                         const style = document.createElement('style');
                         style.textContent = `
                             @keyframes scanDown {{
                                 0% {{ top: -2px; opacity: 0; }}
                                 10% {{ opacity: 1; }}
                                 90% {{ opacity: 1; }}
                                 100% {{ top: 100vh; opacity: 0; }}
                             }}
                         `;
                         document.head.appendChild(style);
                         
                         // Déclencher le scan après 2 secondes
                         setTimeout(createScanLine, 2000);
                         
                         // Auto-fermeture après 30 secondes
                         let countdownTimer;
                         setTimeout(() => {{
                             const button = document.querySelector('.close-button');
                             let countdown = 10;
                             
                             button.style.animation = 'cardGlow 0.5s ease-in-out infinite alternate';
                             
                             countdownTimer = setInterval(() => {{
                                 button.textContent = `FERMETURE AUTO DANS ${{countdown}}S`;
                                 countdown--;
                                 
                                 if (countdown < 0) {{
                                     clearInterval(countdownTimer);
                                     closeWindow();
                                 }}
                             }}, 1000);
                         }}, 20000);
                         
                         // Annuler l'auto-fermeture si l'utilisateur interagit
                         document.addEventListener('click', () => {{
                             if (countdownTimer) {{
                                 clearInterval(countdownTimer);
                                 const button = document.querySelector('.close-button');
                                 button.textContent = 'FERMER LA FENÊTRE';
                                 button.style.animation = '';
                             }}
                         }});
                     }});
                 </script>
            </body>
            </html>
            """.encode('utf-8')
            
            self.wfile.write(html)
            
        except Exception as e:
            print(f"Erreur handler: {e}")
            self.send_error(500, f"Erreur serveur: {str(e)}")
    
    def log_message(self, format, *args):
        """Désactiver les logs Vercel verbeux"""
        pass 