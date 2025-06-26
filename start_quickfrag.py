#!/usr/bin/env python3
"""
🚀 QuickFrag - Lanceur principal
Lance le bot Discord ET le serveur Steam callback ensemble
"""

import subprocess
import sys
import time
import signal
import os
from multiprocessing import Process

def run_discord_bot():
    """Lance le bot Discord"""
    print("🤖 Démarrage du bot Discord...")
    subprocess.run([sys.executable, "QuickFrag.py"])

def run_steam_server():
    """Lance le serveur Steam callback"""
    print("🌐 Démarrage du serveur Steam callback...")
    subprocess.run([sys.executable, "steam_callback_server.py"])

def signal_handler(sig, frame):
    """Gestionnaire pour arrêter proprement les services"""
    print("\n🛑 Arrêt de QuickFrag...")
    sys.exit(0)

def main():
    """Fonction principale"""
    print("🎯 QuickFrag - Démarrage des services...")
    print("=" * 50)
    
    # Vérifier les variables d'environnement
    required_vars = ["DISCORD_TOKEN", "SUPABASE_URL", "SUPABASE_ANON_KEY"]
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Variables d'environnement manquantes: {', '.join(missing_vars)}")
        print("💡 Ajoutez-les à votre fichier .env ou export")
        sys.exit(1)
    
    # Vérifier si le webhook Discord est configuré
    if not os.getenv("DISCORD_WEBHOOK_URL"):
        print("⚠️  DISCORD_WEBHOOK_URL non configuré - pas de notifications Discord")
    
    # Gestionnaire de signal pour arrêt propre
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Lancer les deux processus
        print("🤖 Lancement du bot Discord...")
        discord_process = Process(target=run_discord_bot)
        discord_process.start()
        
        # Petite pause
        time.sleep(2)
        
        print("🌐 Lancement du serveur Steam callback...")
        steam_process = Process(target=run_steam_server)
        steam_process.start()
        
        print("✅ Services démarrés !")
        print("📍 Bot Discord: Actif")
        print("📍 Serveur Steam: http://localhost:5000/steam-callback")
        print("📍 Santé: http://localhost:5000/health")
        print("=" * 50)
        print("👀 Appuyez sur Ctrl+C pour arrêter")
        
        # Attendre que les processus se terminent
        discord_process.join()
        steam_process.join()
        
    except KeyboardInterrupt:
        print("\n🛑 Arrêt demandé...")
        
        # Arrêter les processus
        if 'discord_process' in locals() and discord_process.is_alive():
            discord_process.terminate()
            discord_process.join(timeout=5)
        
        if 'steam_process' in locals() and steam_process.is_alive():
            steam_process.terminate()
            steam_process.join(timeout=5)
        
        print("✅ Services arrêtés proprement")

if __name__ == "__main__":
    main() 