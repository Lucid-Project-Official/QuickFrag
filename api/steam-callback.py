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
                <title>QFWhitelist - Connexion Réussie</title>
                <meta charset="utf-8">
                <meta name="viewport" content="width=device-width, initial-scale=1.0">
                <style>
                    @import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;700;900&family=Rajdhani:wght@300;400;600;700&display=swap');
                    
                    * {{
                        margin: 0;
                        padding: 0;
                        box-sizing: border-box;
                    }}
                    
                    body {{
                        font-family: 'Rajdhani', sans-serif;
                        background: linear-gradient(135deg, #0c0c0c 0%, #1a1a2e 25%, #16213e 50%, #0f0f23 75%, #000000 100%);
                        min-height: 100vh;
                        overflow-x: hidden;
                        position: relative;
                        display: flex;
                        align-items: center;
                        justify-content: center;
                    }}
                    
                    /* Particules d'arrière-plan */
                    .particles {{
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        pointer-events: none;
                        z-index: 1;
                    }}
                    
                    .particle {{
                        position: absolute;
                        width: 2px;
                        height: 2px;
                        background: #00ff88;
                        border-radius: 50%;
                        animation: float 6s infinite ease-in-out;
                        box-shadow: 0 0 10px #00ff88;
                    }}
                    
                    /* Éléments 3D flottants CS2 */
                    .cs2-elements {{
                        position: fixed;
                        top: 0;
                        left: 0;
                        width: 100%;
                        height: 100%;
                        pointer-events: none;
                        z-index: 2;
                    }}
                    
                    .cs2-item {{
                        position: absolute;
                        font-size: 40px;
                        opacity: 0.6;
                        animation: cs2Float 8s infinite ease-in-out;
                        filter: drop-shadow(0 0 15px rgba(255, 69, 0, 0.5));
                    }}
                    
                    .ak47 {{
                        color: #ff4500;
                        font-size: 35px;
                        animation-delay: -1s;
                        top: 20%;
                        left: 10%;
                    }}
                    
                    .smoke {{
                        color: #808080;
                        font-size: 30px;
                        animation-delay: -3s;
                        top: 60%;
                        right: 15%;
                    }}
                    
                    .flash {{
                        color: #ffff00;
                        font-size: 25px;
                        animation-delay: -2s;
                        top: 30%;
                        right: 20%;
                    }}
                    
                    .bomb {{
                        color: #ff0000;
                        font-size: 32px;
                        animation-delay: -4s;
                        bottom: 30%;
                        left: 15%;
                    }}
                    
                    .awp {{
                        color: #4169e1;
                        font-size: 38px;
                        animation-delay: -0.5s;
                        top: 10%;
                        right: 30%;
                    }}
                    
                    .knife {{
                        color: #c0c0c0;
                        font-size: 28px;
                        animation-delay: -2.5s;
                        bottom: 20%;
                        right: 10%;
                    }}
                    
                    /* Conteneur principal */
                    .container {{
                        position: relative;
                        z-index: 10;
                        max-width: 600px;
                        width: 90%;
                        padding: 0 20px;
                    }}
                    
                    .success-card {{
                        background: linear-gradient(145deg, rgba(15, 15, 35, 0.95), rgba(26, 26, 46, 0.95));
                        border: 2px solid transparent;
                        background-clip: padding-box;
                        border-radius: 20px;
                        padding: 40px;
                        text-align: center;
                        position: relative;
                        backdrop-filter: blur(20px);
                        box-shadow: 
                            0 25px 50px rgba(0, 0, 0, 0.5),
                            inset 0 1px 0 rgba(255, 255, 255, 0.1),
                            0 0 0 1px rgba(0, 255, 136, 0.2);
                        animation: cardGlow 3s ease-in-out infinite alternate;
                    }}
                    
                    .success-card::before {{
                        content: '';
                        position: absolute;
                        top: -2px;
                        left: -2px;
                        right: -2px;
                        bottom: -2px;
                        background: linear-gradient(45deg, #00ff88, #0066ff, #ff0066, #00ff88);
                        border-radius: 22px;
                        z-index: -1;
                        animation: borderRotate 4s linear infinite;
                    }}
                    
                    .logo {{
                        font-family: 'Orbitron', monospace;
                        font-size: 2.5rem;
                        font-weight: 900;
                        color: #00ff88;
                        margin-bottom: 30px;
                        text-shadow: 0 0 30px rgba(0, 255, 136, 0.5);
                        animation: logoFloat 2s ease-in-out infinite alternate;
                    }}
                    
                    .status-icon {{
                        font-size: 4rem;
                        margin-bottom: 20px;
                        animation: iconPulse 2s ease-in-out infinite;
                    }}
                    
                    .title {{
                        font-family: 'Orbitron', monospace;
                        font-size: 2rem;
                        font-weight: 700;
                        color: #ffffff;
                        margin-bottom: 20px;
                        text-shadow: 0 0 20px rgba(255, 255, 255, 0.3);
                    }}
                    
                    .description {{
                        font-size: 1.2rem;
                        color: #b0b0b0;
                        margin-bottom: 30px;
                        line-height: 1.6;
                    }}
                    
                    .steam-info {{
                        background: linear-gradient(90deg, rgba(0, 255, 136, 0.1), rgba(0, 102, 255, 0.1));
                        border: 1px solid rgba(0, 255, 136, 0.3);
                        border-radius: 15px;
                        padding: 20px;
                        margin: 20px 0;
                    }}
                    
                    .steam-id {{
                        font-family: 'Orbitron', monospace;
                        font-size: 1.3rem;
                        color: #00ff88;
                        font-weight: 600;
                        word-break: break-all;
                    }}
                    
                    .tech-text {{
                        font-size: 0.9rem;
                        color: #808080;
                        margin-top: 30px;
                        font-style: italic;
                    }}
                    
                    /* Animations */
                    @keyframes float {{
                        0%, 100% {{ transform: translateY(0px) rotate(0deg); opacity: 0; }}
                        50% {{ transform: translateY(-20px) rotate(180deg); opacity: 1; }}
                    }}
                    
                    @keyframes cs2Float {{
                        0% {{ transform: translateY(0px) rotateZ(0deg) scale(1); }}
                        25% {{ transform: translateY(-30px) rotateZ(90deg) scale(1.1); }}
                        50% {{ transform: translateY(-15px) rotateZ(180deg) scale(0.9); }}
                        75% {{ transform: translateY(-40px) rotateZ(270deg) scale(1.05); }}
                        100% {{ transform: translateY(0px) rotateZ(360deg) scale(1); }}
                    }}
                    
                    @keyframes cardGlow {{
                        0% {{ box-shadow: 0 25px 50px rgba(0, 0, 0, 0.5), inset 0 1px 0 rgba(255, 255, 255, 0.1), 0 0 0 1px rgba(0, 255, 136, 0.2); }}
                        100% {{ box-shadow: 0 25px 60px rgba(0, 255, 136, 0.2), inset 0 1px 0 rgba(255, 255, 255, 0.2), 0 0 0 1px rgba(0, 255, 136, 0.4); }}
                    }}
                    
                    @keyframes borderRotate {{
                        0% {{ transform: rotate(0deg); }}
                        100% {{ transform: rotate(360deg); }}
                    }}
                    
                    @keyframes logoFloat {{
                        0% {{ transform: translateY(0px); }}
                        100% {{ transform: translateY(-10px); }}
                    }}
                    
                    @keyframes iconPulse {{
                        0%, 100% {{ transform: scale(1); }}
                        50% {{ transform: scale(1.1); }}
                    }}
                    
                    /* Responsive */
                    @media (max-width: 768px) {{
                        .logo {{ font-size: 2rem; }}
                        .title {{ font-size: 1.5rem; }}
                        .description {{ font-size: 1rem; }}
                        .success-card {{ padding: 30px 20px; }}
                        .cs2-item {{ font-size: 25px; }}
                    }}
                </style>
            </head>
            <body>
                <!-- Particules d'arrière-plan -->
                <div class="particles" id="particles"></div>
                
                <!-- Éléments 3D CS2 flottants -->
                <div class="cs2-elements">
                    <div class="cs2-item ak47">🔫</div>
                    <div class="cs2-item smoke">💨</div>
                    <div class="cs2-item flash">💥</div>
                    <div class="cs2-item bomb">💣</div>
                    <div class="cs2-item awp">🎯</div>
                    <div class="cs2-item knife">🔪</div>
                </div>
                
                <div class="container">
                    <div class="success-card">
                        <div class="logo">QFWhitelist</div>
                        <div class="status-icon">✅</div>
                        <h1 class="title">CONNEXION ÉTABLIE</h1>
                        <p class="description">
                            Votre compte Steam a été synchronisé avec succès à notre système QFWhitelist.
                            <br>Préparation de l'accès aux serveurs en cours...
                        </p>
                        
                        <div class="steam-info">
                            <div style="color: #ffffff; margin-bottom: 10px; font-weight: 600;">STEAM ID AUTHENTIFIÉ</div>
                            <div class="steam-id">{steam_id}</div>
                        </div>
                        
                        <div style="margin: 30px 0; padding: 15px; background: rgba(0, 255, 136, 0.05); border-radius: 10px; border-left: 4px solid #00ff88;">
                            <div style="color: #00ff88; font-weight: 600; margin-bottom: 5px;">🎮 STATUT INITIAL</div>
                            <div style="color: #ffffff;">Rang: Silver I • ELO: 1000 pts</div>
                        </div>
                        
                        <p class="tech-text">
                            Notification Discord envoyée • Session sécurisée • Accès autorisé
                            <br>Vous pouvez maintenant fermer cette fenêtre
                        </p>
                    </div>
                </div>
                
                <script>
                    // Génération dynamique des particules
                    function createParticles() {{
                        const particlesContainer = document.getElementById('particles');
                        const particleCount = 50;
                        
                        for (let i = 0; i < particleCount; i++) {{
                            const particle = document.createElement('div');
                            particle.className = 'particle';
                            particle.style.left = Math.random() * 100 + '%';
                            particle.style.top = Math.random() * 100 + '%';
                            particle.style.animationDelay = Math.random() * 6 + 's';
                            particle.style.animationDuration = (Math.random() * 4 + 4) + 's';
                            particlesContainer.appendChild(particle);
                        }}
                    }}
                    
                    // Animation des éléments CS2
                    function animateCS2Elements() {{
                        const elements = document.querySelectorAll('.cs2-item');
                        elements.forEach((element, index) => {{
                            setInterval(() => {{
                                const randomX = Math.random() * 100;
                                const randomY = Math.random() * 100;
                                element.style.left = randomX + '%';
                                element.style.top = randomY + '%';
                            }}, 8000 + (index * 1000));
                        }});
                    }}
                    
                    // Initialisation
                    document.addEventListener('DOMContentLoaded', function() {{
                        createParticles();
                        animateCS2Elements();
                        
                        // Auto-redirection après 10 secondes
                        setTimeout(() => {{
                            window.close();
                        }}, 10000);
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