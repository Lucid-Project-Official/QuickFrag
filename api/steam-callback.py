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
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&display=swap');
                    
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Orbitron', monospace;
                        background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 25%, #16213e 50%, #0f3460 75%, #003366 100%);
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
                        line-height: 1.2;
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
                        line-height: 1.4;
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
                        line-height: 1.6;
                    }}
                    
                    .steam-id {{
                        font-size: 1.5rem;
                        font-weight: 700;
                        color: #00ffff;
                        margin-bottom: 10px;
                        word-break: break-all;
                    }}
                    
                    .discord-info {{
                        color: #7289da;
                        font-size: 1.1rem;
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
                        width: 100%;
                        max-width: 300px;
                    }}
                    
                    .close-button:hover {{
                        transform: translateY(-2px) scale(1.05);
                        box-shadow: 0 8px 25px rgba(0, 255, 255, 0.7);
                        background: linear-gradient(45deg, #00ffff, #ff6b6b);
                    }}
                    
                    .close-button:active {{
                        transform: translateY(0) scale(0.98);
                    }}
                    
                    /* Responsive Design */
                    @media screen and (max-width: 1200px) {{
                        .main-container {{
                            padding: 15px;
                        }}
                        .success-card {{
                            max-width: 500px;
                        }}
                    }}
                    
                    @media screen and (max-width: 768px) {{
                        .main-container {{
                            padding: 10px;
                        }}
                        .success-card {{
                            padding: 30px 25px;
                            margin: 10px;
                            border-radius: 15px;
                        }}
                        .success-title {{
                            font-size: 2rem;
                            margin-bottom: 15px;
                        }}
                        .success-subtitle {{
                            font-size: 1rem;
                            margin-bottom: 25px;
                        }}
                        .steam-info {{
                            padding: 15px;
                            margin: 15px 0;
                        }}
                        .steam-id {{
                            font-size: 1.2rem;
                        }}
                        .discord-info {{
                            font-size: 1rem;
                        }}
                        .close-button {{
                            padding: 12px 25px;
                            font-size: 1rem;
                            margin-top: 25px;
                        }}
                    }}
                    
                    @media screen and (max-width: 480px) {{
                        .main-container {{
                            padding: 5px;
                        }}
                        .success-card {{
                            padding: 25px 20px;
                            margin: 5px;
                            border-radius: 12px;
                        }}
                        .success-title {{
                            font-size: 1.6rem;
                            margin-bottom: 12px;
                        }}
                        .success-subtitle {{
                            font-size: 0.9rem;
                            margin-bottom: 20px;
                        }}
                        .steam-info {{
                            padding: 12px;
                            margin: 12px 0;
                        }}
                        .steam-id {{
                            font-size: 1rem;
                            margin-bottom: 8px;
                        }}
                        .discord-info {{
                            font-size: 0.9rem;
                        }}
                        .close-button {{
                            padding: 10px 20px;
                            font-size: 0.9rem;
                            margin-top: 20px;
                        }}
                        .success-card p {{
                            font-size: 0.9rem;
                        }}
                    }}
                    
                    @media screen and (max-width: 360px) {{
                        .success-title {{
                            font-size: 1.4rem;
                        }}
                        .success-subtitle {{
                            font-size: 0.8rem;
                        }}
                        .steam-id {{
                            font-size: 0.9rem;
                        }}
                        .discord-info {{
                            font-size: 0.8rem;
                        }}
                        .success-card p {{
                            font-size: 0.8rem;
                        }}
                    }}
                    
                    /* Landscape orientation sur mobile */
                    @media screen and (max-height: 500px) and (orientation: landscape) {{
                        .main-container {{
                            padding: 10px;
                            justify-content: flex-start;
                            padding-top: 20px;
                        }}
                        .success-card {{
                            padding: 20px;
                            margin: 0;
                        }}
                        .success-title {{
                            font-size: 1.5rem;
                            margin-bottom: 10px;
                        }}
                        .success-subtitle {{
                            font-size: 0.9rem;
                            margin-bottom: 15px;
                        }}
                        .steam-info {{
                            padding: 10px;
                            margin: 10px 0;
                        }}
                        .close-button {{
                            margin-top: 15px;
                            padding: 8px 20px;
                        }}
                    }}
                </style>
            </head>
            <body>
                <div class="stars"></div>
                
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
                        // Essayer de fermer l'onglet en utilisant window.close()
                        if (window.history.length > 1) {{
                            // Si l'onglet a un historique, revenir en arrière
                            window.history.back();
                        }} else {{
                            // Essayer plusieurs méthodes pour fermer la fenêtre/onglet
                            try {{
                                // Méthode 1: Fermeture directe
                                window.close();
                            }} catch(e) {{
                                console.log('window.close() failed:', e);
                            }}
                            
                            // Méthode 2: Redirection vers une page vide puis fermeture
                            setTimeout(() => {{
                                try {{
                                    window.location.href = 'about:blank';
                                    window.close();
                                }} catch(e) {{
                                    console.log('about:blank method failed:', e);
                                }}
                            }}, 100);
                            
                            // Méthode 3: Demander à l'utilisateur de fermer manuellement
                            setTimeout(() => {{
                                const isMobile = /Android|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
                                const message = isMobile ? 
                                    'Vous pouvez fermer cet onglet maintenant.' :
                                    'Vous pouvez fermer cet onglet (Ctrl+W ou ⌘+W)';
                                alert(message);
                            }}, 500);
                        }}
                    }}
                    
                    // Gestion des animations d'entrée
                    document.addEventListener('DOMContentLoaded', function() {{
                        // Créer les étoiles avec délai
                        setTimeout(createStars, 500);
                        
                        // Audio feedback (optionnel) pour l'entrée
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
                        
                        // Déclencher le son d'entrée après 1 seconde (interaction utilisateur requise)
                        document.addEventListener('click', playEntranceSound, {{ once: true }});
                        
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
                        
                        // Gestion du raccourci clavier pour fermer (Escape)
                        document.addEventListener('keydown', function(event) {{
                            if (event.key === 'Escape') {{
                                closeWindow();
                            }}
                        }});
                        
                        // Feedback visuel pour le bouton
                        const button = document.querySelector('.close-button');
                        if (button) {{
                            button.addEventListener('mousedown', function() {{
                                this.style.transform = 'translateY(2px) scale(0.95)';
                            }});
                            
                            button.addEventListener('mouseup', function() {{
                                this.style.transform = 'translateY(-2px) scale(1.05)';
                            }});
                            
                            button.addEventListener('mouseleave', function() {{
                                this.style.transform = 'translateY(0) scale(1)';
                            }});
                        }}
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