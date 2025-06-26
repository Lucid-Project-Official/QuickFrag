#!/usr/bin/env python3
"""
🎯 QuickFrag - Serveur Steam Callback Minimal
Tourne sur le même serveur que le bot Discord
Port 5000 par défaut
"""

from flask import Flask, request
import requests
import re
import os
import json
from supabase import create_client, Client

app = Flask(__name__)

# Utiliser les mêmes variables d'environnement que le bot Discord
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
DISCORD_WEBHOOK = os.getenv("DISCORD_WEBHOOK_URL")  # Nouvelle variable à ajouter

# Initialiser Supabase
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def verify_steam_openid(params):
    """Vérifie la réponse Steam OpenID"""
    try:
        verify_params = dict(params)
        verify_params["openid.mode"] = "check_authentication"
        
        response = requests.post(
            "https://steamcommunity.com/openid/login",
            data=verify_params,
            timeout=10
        )
        
        if "is_valid:true" in response.text:
            identity_url = params.get("openid.identity", "")
            steam_id_match = re.search(r'steamcommunity\.com/openid/id/(\d+)', identity_url)
            return steam_id_match.group(1) if steam_id_match else None
        
        return None
    except Exception as e:
        print(f"Erreur vérification Steam: {e}")
        return None

def send_discord_webhook(discord_user_id, steam_id):
    """Envoie un message Discord via webhook"""
    if not DISCORD_WEBHOOK:
        print("Pas de webhook Discord configuré")
        return
        
    try:
        embed = {
            "title": "✅ Compte Steam lié avec succès !",
            "description": f"Votre compte Steam a été lié à votre compte Discord.\n\n**Steam ID**: {steam_id}\n**Rang initial**: Silver I\n**ELO initial**: 1000",
            "color": 3066993
        }
        
        data = {
            "content": f"<@{discord_user_id}>",
            "embeds": [embed]
        }
        
        requests.post(DISCORD_WEBHOOK, json=data, timeout=10)
        print(f"Notification Discord envoyée pour {discord_user_id}")
        
    except Exception as e:
        print(f"Erreur envoi Discord: {e}")

@app.route('/steam-callback')
def steam_callback():
    """Endpoint principal pour les callbacks Steam"""
    try:
        # Récupérer les paramètres
        discord_user_id = request.args.get('discord_id')
        token = request.args.get('token')
        
        if not discord_user_id or not token:
            return "❌ Paramètres manquants", 400
        
        # Vérifier Steam OpenID
        steam_id = verify_steam_openid(request.args)
        if not steam_id:
            return "❌ Vérification Steam échouée", 400
        
        # Vérifier si Steam ID déjà utilisé
        existing = supabase.table("Players").select("Discord_PlayerID").eq("Steam_PlayerID", steam_id).execute()
        if existing.data:
            return "❌ Ce compte Steam est déjà lié à un autre utilisateur Discord", 400
        
        # Créer ou mettre à jour l'entrée
        player_response = supabase.table("Players").select("*").eq("Discord_PlayerID", str(discord_user_id)).execute()
        
        if player_response.data:
            # Mettre à jour
            supabase.table("Players").update({
                "Steam_PlayerID": steam_id,
                "PlayerRank": "SilverOne",
                "PlayerElo": 1000
            }).eq("Discord_PlayerID", str(discord_user_id)).execute()
        else:
            # Créer nouveau
            supabase.table("Players").insert({
                "Steam_PlayerID": steam_id,
                "Discord_PlayerID": str(discord_user_id),
                "PlayerName": f"User_{discord_user_id}",
                "PlayerRank": "SilverOne",
                "PlayerElo": 1000
            }).execute()
        
        # Envoyer notification Discord
        send_discord_webhook(discord_user_id, steam_id)
        
        # Page de succès simple
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>QuickFrag - Liaison réussie</title>
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
                <p>Vous pouvez maintenant fermer cette page.</p>
            </div>
        </body>
        </html>
        """, 200
        
    except Exception as e:
        print(f"Erreur dans steam_callback: {e}")
        return f"❌ Erreur serveur: {str(e)}", 500

@app.route('/health')
def health():
    """Point de santé"""
    return {"status": "healthy", "service": "QuickFrag Steam Callback"}

@app.route('/')
def home():
    """Page d'accueil minimaliste"""
    return """
    <!DOCTYPE html>
    <html>
    <head><title>QuickFrag Steam Auth</title></head>
    <body style="font-family:Arial;text-align:center;padding:50px;">
        <h1>🎮 QuickFrag Steam Auth</h1>
        <p>Service d'authentification Steam pour QuickFrag</p>
    </body>
    </html>
    """

if __name__ == '__main__':
    # En développement
    app.run(host='0.0.0.0', port=5000, debug=False) 