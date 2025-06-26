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

def send_discord_webhook(discord_id, steam_id):
    """Envoie webhook Discord avec urllib"""
    try:
        webhook_url = os.environ.get("DISCORD_WEBHOOK_URL")
        if not webhook_url:
            return
        
        embed = {
            "title": "✅ Compte Steam lié avec succès !",
            "description": f"Votre compte Steam a été lié à votre compte Discord.\n\n**Steam ID**: {steam_id}\n**Rang initial**: Silver I\n**ELO initial**: 1000",
            "color": 3066993
        }
        
        data = {
            "content": f"<@{discord_id}>",
            "embeds": [embed]
        }
        
        json_data = json.dumps(data).encode('utf-8')
        req = urllib.request.Request(webhook_url, data=json_data)
        req.add_header("Content-Type", "application/json")
        
        urllib.request.urlopen(req, timeout=10)
        
    except Exception as e:
        print(f"Erreur Discord: {e}")

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
            send_discord_webhook(discord_id, steam_id)
            
            # Page de succès
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>QuickFrag - Succès</title>
                <meta charset="utf-8">
                <style>
                    body {{ font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f0f0; }}
                    .success {{ background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }}
                    h1 {{ color: #27ae60; }}
                </style>
            </head>
            <body>
                <div class="success">
                    <h1>✅ Compte lié avec succès !</h1>
                    <p>Votre compte Steam a été lié à votre compte Discord.</p>
                    <p><strong>Steam ID:</strong> {steam_id}</p>
                    <p>Vous devriez recevoir une confirmation sur Discord.</p>
                    <p>Vous pouvez fermer cette page.</p>
                </div>
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