import discord, asyncio, re, json, subprocess, random, os, sys, getpass, platform, urllib.parse, uuid, hashlib, time
from discord.ext import commands
from discord import app_commands
from supabase import create_client, Client
from pathlib import Path
import aiohttp

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

CLE_DISCORD = os.getenv("DISCORD_TOKEN")
EMOTES_DIR = "Emotes"

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


countdown_flags = {}

# Dictionnaire pour stocker les tokens de liaison Steam temporaires
steam_link_tokens = {}

def generate_steam_auth_url(discord_user_id):
    """Génère un URL d'authentification Steam unique pour un utilisateur Discord"""
    # Générer un token unique
    token = str(uuid.uuid4())
    timestamp = int(time.time())
    
    # Stocker le token avec l'ID Discord et un timestamp
    steam_link_tokens[token] = {
        "discord_user_id": discord_user_id,
        "timestamp": timestamp
    }
    
    # URL de base Steam OpenID
    steam_openid_url = "https://steamcommunity.com/openid/login"
    
    # Paramètres pour Steam OpenID
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": f"https://quickfrag-hgxkr4z3x-linoxyrs-projects.vercel.app/api/steam-callback?token={token}&discord_id={discord_user_id}",
        "openid.realm": "https://quickfrag.vercel.app",
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select"
    }
    
    # Construire l'URL complète
    auth_url = steam_openid_url + "?" + urllib.parse.urlencode(params)
    return auth_url, token

async def verify_steam_openid(response_params):
    """Vérifie la réponse Steam OpenID et extrait le Steam ID"""
    try:
        # Préparer les paramètres de vérification
        verify_params = dict(response_params)
        verify_params["openid.mode"] = "check_authentication"
        
        # Faire la requête de vérification à Steam
        async with aiohttp.ClientSession() as session:
            async with session.post(
                "https://steamcommunity.com/openid/login",
                data=verify_params
            ) as response:
                verify_response = await response.text()
                
                if "is_valid:true" in verify_response:
                    # Extraire le Steam ID de l'identity URL
                    identity_url = response_params.get("openid.identity", "")
                    steam_id_match = re.search(r'steamcommunity\.com/openid/id/(\d+)', identity_url)
                    
                    if steam_id_match:
                        return steam_id_match.group(1)
                
        return None
    except Exception as e:
        print(f"Erreur lors de la vérification Steam OpenID: {e}")
        return None

async def check_steam_link_required(interaction, action_description="participer"):
    """Vérifie si l'utilisateur a un compte Steam lié. Retourne True si lié, False sinon."""
    user_id = interaction.user.id
    
    # Vérification du compte Steam lié
    player_steam_response = supabase.table("Players").select(
        "Steam_PlayerID"
    ).eq("Discord_PlayerID", str(user_id)).execute()
    
    player_exists = False
    steam_id_valid = False
    
    if player_steam_response.data:
        player_data = player_steam_response.data[0]
        player_exists = True
        steam_id = player_data.get("Steam_PlayerID")
        if steam_id and str(steam_id).strip() and str(steam_id).strip() != "None":
            steam_id_valid = True
    
    if not player_exists or not steam_id_valid:
        # Générer le lien d'authentification Steam
        auth_url, token = generate_steam_auth_url(user_id)
        
        if not player_exists:
            # Créer une nouvelle ligne avec le Discord_PlayerID
            supabase.table("Players").insert({
                "Discord_PlayerID": str(user_id)
            }).execute()
        
        embed = discord.Embed(
            title="🔗 Liaison compte Steam requise",
            description=f"Vous devez lier votre compte Steam à votre compte Discord pour {action_description}.",
            color=discord.Color.orange()
        )
        embed.add_field(
            name="📋 Instructions",
            value="1. Cliquez sur le lien ci-dessous\n"
                  "2. Connectez-vous à votre compte Steam\n"
                  "3. Autorisez la liaison\n"
                  "4. Vous recevrez une confirmation par message privé\n"
                  "5. Vous pourrez ensuite continuer",
            inline=False
        )
        embed.add_field(
            name="🔗 Lien de liaison Steam",
            value=f"[**Cliquer ici pour lier votre compte Steam**]({auth_url})",
            inline=False
        )
        embed.set_footer(text="Ce lien expire dans 2 minutes")
        
        await interaction.followup.send(embed=embed, ephemeral=True)
        return False
    
    return True

async def handle_steam_callback(token, steam_response_params):
    """Traite le callback de Steam et lie le compte"""
    if token not in steam_link_tokens:
        return False, "Token invalide ou expiré"
    
    token_data = steam_link_tokens[token]
    discord_user_id = token_data["discord_user_id"]
    
    # Vérifier que le token n'est pas trop ancien (2 minutes max)
    if time.time() - token_data["timestamp"] > 120:
        del steam_link_tokens[token]
        return False, "Token expiré"
    
    # Vérifier la réponse Steam
    steam_id = await verify_steam_openid(steam_response_params)
    
    if not steam_id:
        return False, "Échec de la vérification Steam"
    
    try:
        # Vérifier si ce Steam ID est déjà lié à un autre compte Discord
        existing_player_response = supabase.table("Players").select(
            "Discord_PlayerID"
        ).eq("Steam_PlayerID", steam_id).execute()
        
        if existing_player_response.data:
            return False, "Ce compte Steam est déjà lié à un autre compte Discord"
        
        # Obtenir l'utilisateur Discord
        user = bot.get_user(int(discord_user_id))
        if not user:
            return False, "Utilisateur Discord introuvable"
        
        # Vérifier si l'utilisateur existe déjà dans la table Players
        player_response = supabase.table("Players").select("*").eq(
            "Discord_PlayerID", str(discord_user_id)
        ).execute()
        
        if player_response.data:
            # Mettre à jour l'entrée existante
            supabase.table("Players").update({
                "Steam_PlayerID": steam_id,
                "PlayerName": user.name,
                "PlayerRank": "SilverOne",
                "PlayerElo": 1000
            }).eq("Discord_PlayerID", str(discord_user_id)).execute()
        else:
            # Créer une nouvelle entrée
            supabase.table("Players").insert({
                "Steam_PlayerID": steam_id,
                "Discord_PlayerID": str(discord_user_id),
                "PlayerName": user.name,
                "PlayerRank": "SilverOne",
                "PlayerElo": 1000
            }).execute()
        
        # Envoyer un message de confirmation à l'utilisateur
        try:
            embed = discord.Embed(
                title="✅ Compte Steam lié avec succès !",
                description=f"Votre compte Steam a été lié à votre compte Discord.\n\n"
                           f"**Steam ID**: {steam_id}\n"
                           f"**Rang initial**: Silver I\n"
                           f"**ELO initial**: 1000",
                color=discord.Color.green()
            )
            await user.send(embed=embed)
        except discord.Forbidden:
            print(f"Impossible d'envoyer un message privé à {user.name}")
        
        # Nettoyer le token
        del steam_link_tokens[token]
        
        return True, "Compte lié avec succès"
        
    except Exception as e:
        print(f"Erreur lors de la liaison du compte: {e}")
        return False, f"Erreur lors de la liaison: {str(e)}"

async def sync_all_emojis():
    # Liste tous les fichiers .webp du dossier
    emote_files = [f for f in os.listdir(EMOTES_DIR) if f.lower().endswith(".webp")]

    for guild in bot.guilds:
        print(f"\n🔍 Traitement du serveur : {guild.name}")
        for filename in emote_files:
            emoji_name = os.path.splitext(filename)[0]

            # Vérifie si l'émoji est déjà présent
            if any(e.name == emoji_name for e in guild.emojis):
                print(f"✅ Emoji '{emoji_name}' déjà présent")
                continue

            try:
                with open(os.path.join(EMOTES_DIR, filename), "rb") as image_file:
                    image_data = image_file.read()

                await guild.create_custom_emoji(name=emoji_name, image=image_data)
                print(f"🎉 Emoji '{emoji_name}' ajouté à {guild.name}")

            except discord.Forbidden:
                print(f"❌ Permission refusée dans : {guild.name}")
            except discord.HTTPException as e:
                print(f"❌ Erreur HTTP pour '{emoji_name}' dans {guild.name} : {e}")

def truncate_message_for_discord(message: str, max_length: int = 2000) -> str:
    """Tronque un message pour respecter les limites de Discord"""
    if len(message) <= max_length:
        return message
    
    # Laisser de la place pour "..."
    truncated_length = max_length - 3
    return message[:truncated_length] + "..."

def format_server_output(sshadress: str, stderr: str, stdout: str, max_total_length: int = 1800) -> str:
    """Formate la sortie du serveur en respectant les limites de longueur"""
    base_message = f"Serveur: {sshadress}\n"
    base_length = len(base_message)
    
    # Calculer l'espace disponible pour stderr et stdout
    available_space = max_total_length - base_length - 20  # 20 pour les labels et sauts de ligne
    
    if available_space <= 0:
        return base_message + "Sortie trop longue pour être affichée."
    
    # Diviser l'espace équitablement entre stderr et stdout
    space_per_output = available_space // 2
    
    stderr_truncated = stderr[:space_per_output] + ("..." if len(stderr) > space_per_output else "")
    stdout_truncated = stdout[:space_per_output] + ("..." if len(stdout) > space_per_output else "")
    
    return base_message + f"STDERR:\n{stderr_truncated}\n\nSTDOUT:\n{stdout_truncated}"

async def update_all_linked_messages_with_starting_server(match_id, countdown_seconds=30):
    """Met à jour tous les messages liés avec le bouton de démarrage du serveur"""
    # Récupération des messages liés
    linked_msgs_response = supabase.table("Matchs").select(
        "Linked_Embbeded_MSG_1, Linked_Embbeded_MSG_2, Linked_Embbeded_MSG_3, "
        "Linked_Embbeded_MSG_4, Linked_Embbeded_MSG_5, Linked_Embbeded_MSG_6, "
        "Linked_Embbeded_MSG_7, Linked_Embbeded_MSG_8, Linked_Embbeded_MSG_9, "
        "Linked_Embbeded_MSG_10"
    ).eq("match_ID", match_id).eq("match_Status", 2).execute()
    
    result = linked_msgs_response.data[0] if linked_msgs_response.data else None
    
    if result:
        data_listed = [data for data in result.values() if data]  # filtre les None
        for data_dict in data_listed:
            try:
                dict_data = json.loads(data_dict)
                channel = bot.get_channel(int(dict_data['channel_id']))
                if channel:
                    message = await channel.fetch_message(int(dict_data['message_id']))
                    if message:
                        # Récupérer l'embed existant
                        current_embed = message.embeds[0] if message.embeds else None
                        
                        # Créer la vue avec le bouton de démarrage
                        quit_button = QuitButton()
                        starting_view = StartingServerViewButtons(quit_button, countdown_seconds)
                        
                        await message.edit(embed=current_embed, view=starting_view)
            except (json.JSONDecodeError, discord.NotFound, discord.Forbidden) as e:
                print(f"Erreur lors de la mise à jour du message: {e}")
                continue

async def create_connect_embed(match_id, guild):
    """Crée l'embed avec les joueurs et l'emoji spécifique pour chaque joueur basé sur son rang"""
    # Récupération du nom du créateur
    response = supabase.table("Matchs").select("match_CreatorName").eq("match_ID", match_id).execute()
    
    CreatorName = ""
    if response.data and len(response.data) > 0:
        CreatorName = response.data[0]["match_CreatorName"]
    
    embed = discord.Embed(
        title="🎮 SERVEUR PRÊT - CONNECTEZ-VOUS !",
        description=f"**{CreatorName}** est le créateur de la partie !\nLe serveur est maintenant disponible, connectez-vous !",
        color=discord.Color.green()
    )

    embed.add_field(name="EQUIPE BLEU :", value="🔹", inline=True)
    embed.add_field(name="EQUIPE ROUGE :", value="🔸", inline=True)

    embed.set_thumbnail(url="https://seek-team-prod.s3.fr-par.scw.cloud/users/67c758968e61a685175513.jpg")

    # Récupération des noms et IDs des joueurs
    players_response = supabase.table("Matchs").select(
        "match_PlayerName_1, match_PlayerName_2, match_PlayerName_3, "
        "match_PlayerName_4, match_PlayerName_5, match_PlayerName_6, "
        "match_PlayerName_7, match_PlayerName_8, match_PlayerName_9, "
        "match_PlayerName_10, match_PlayerID_1, match_PlayerID_2, match_PlayerID_3, "
        "match_PlayerID_4, match_PlayerID_5, match_PlayerID_6, "
        "match_PlayerID_7, match_PlayerID_8, match_PlayerID_9, "
        "match_PlayerID_10"
    ).eq("match_ID", match_id).eq("match_Status", 2).execute()
    
    result = players_response.data[0] if players_response.data else None

    if result:
        # Fonction pour obtenir l'emoji du rang d'un joueur
        def get_player_rank_emoji(player_id):
            if not player_id:
                return "🥈"  # Emoji par défaut
            
            # Récupération du rang du joueur dans la table Players
            player_rank_response = supabase.table("Players").select("PlayerRank").eq("Discord_PlayerID", str(player_id)).execute()
            
            if player_rank_response.data and len(player_rank_response.data) > 0:
                player_rank = player_rank_response.data[0]["PlayerRank"]
                
                # Conversion du rang en nom d'emoji (exemple: "SilverOne" → "SilverOneScaled")
                emoji_name = f"{player_rank}Scaled"
                
                # Recherche de l'emoji dans la guild
                for emoji in guild.emojis:
                    if emoji.name == emoji_name:
                        return str(emoji)
            
            # Si l'emoji n'est pas trouvé, utiliser un emoji par défaut
            return "🥈"

        # Construire les listes avec les joueurs et leurs emojis spécifiques
        blue_team_with_emoji = []
        red_team_with_emoji = []
        
        # Équipe bleue (joueurs 1-5)
        for i in range(1, 6):
            player_name = result.get(f"match_PlayerName_{i}")
            if player_name:
                player_id = result.get(f"match_PlayerID_{i}")
                player_emoji = get_player_rank_emoji(player_id)
                blue_team_with_emoji.append(f"{player_name} {player_emoji}")
        
        # Équipe rouge (joueurs 6-10)
        for i in range(6, 11):
            player_name = result.get(f"match_PlayerName_{i}")
            if player_name:
                player_id = result.get(f"match_PlayerID_{i}")
                player_emoji = get_player_rank_emoji(player_id)
                red_team_with_emoji.append(f"{player_name} {player_emoji}")

        embed.set_field_at(0, name="EQUIPE BLEU :", value="🔹 " + '\n🔹 '.join(blue_team_with_emoji) if blue_team_with_emoji else "🔹", inline=True)
        embed.set_field_at(1, name="EQUIPE ROUGE :", value="🔸 " + '\n🔸 '.join(red_team_with_emoji) if red_team_with_emoji else "🔸", inline=True)

    return embed

async def update_all_linked_messages_with_connect_button(match_id):
    """Met à jour tous les messages liés avec le bouton Se connecter"""
    # Récupération de l'adresse IP du serveur
    server_response = supabase.table("ServersManager").select(
        "server_IPAdress"
    ).eq("match_ID", match_id).eq("server_State", 2).execute()
    
    server_data = server_response.data[0] if server_response.data else None
    server_ip = None
    
    if server_data:
        # Extraction de l'IP (enlever le port par défaut s'il existe)
        server_ip = server_data["server_IPAdress"]
        if server_ip.endswith(":27015"):
            server_ip = server_ip[:-6]  # Enlever :27015
        elif server_ip.endswith(":27016"):
            server_ip = server_ip[:-6]  # Enlever :27016
    
    # Récupération des messages liés
    linked_msgs_response = supabase.table("Matchs").select(
        "Linked_Embbeded_MSG_1, Linked_Embbeded_MSG_2, Linked_Embbeded_MSG_3, "
        "Linked_Embbeded_MSG_4, Linked_Embbeded_MSG_5, Linked_Embbeded_MSG_6, "
        "Linked_Embbeded_MSG_7, Linked_Embbeded_MSG_8, Linked_Embbeded_MSG_9, "
        "Linked_Embbeded_MSG_10"
    ).eq("match_ID", match_id).eq("match_Status", 2).execute()
    
    result = linked_msgs_response.data[0] if linked_msgs_response.data else None
    
    if result:
        data_listed = [data for data in result.values() if data]  # filtre les None
        for data_dict in data_listed:
            try:
                dict_data = json.loads(data_dict)
                channel = bot.get_channel(int(dict_data['channel_id']))
                if channel:
                    message = await channel.fetch_message(int(dict_data['message_id']))
                    if message:
                        # Créer le nouvel embed avec les emojis SilverOne (en utilisant le guild du channel)
                        connect_embed = await create_connect_embed(match_id, channel.guild)
                        
                        # Créer la vue avec le bouton Se connecter (avec l'IP du serveur)
                        quit_button = QuitButton()
                        connect_view = ConnectServerViewButtons(quit_button, server_ip)
                        
                        # Utiliser le nouvel embed avec les emojis SilverOne
                        await message.edit(embed=connect_embed, view=connect_view)
            except (json.JSONDecodeError, discord.NotFound, discord.Forbidden) as e:
                print(f"Erreur lors de la mise à jour du message: {e}")
                continue

async def update_server_countdown_real_time(match_id, ssh_command, start_time):
    """Met à jour le compte à rebours en temps réel pendant l'exécution de la commande SSH"""
    max_wait_time = 60
    
    # Démarrer la commande SSH de manière asynchrone
    process = await asyncio.create_subprocess_exec(
        *ssh_command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )
    
    # Créer une tâche pour surveiller le processus
    async def monitor_process():
        stdout, stderr = await process.communicate()
        return process.returncode, stdout.decode(), stderr.decode()
    
    # Démarrer la surveillance du processus
    process_task = asyncio.create_task(monitor_process())
    
    # Boucle de mise à jour du countdown
    while not process_task.done():
        current_time = asyncio.get_event_loop().time()
        elapsed_time = int(current_time - start_time)
        remaining_time = max(0, max_wait_time - elapsed_time)
        
        # Mettre à jour tous les messages avec le temps restant
        await update_all_linked_messages_with_starting_server(match_id, remaining_time)
        
        # Attendre 1 seconde avant la prochaine mise à jour
        try:
            await asyncio.wait_for(asyncio.sleep(1), timeout=1)
        except asyncio.TimeoutError:
            pass
        
        # Arrêter si on dépasse le temps maximum
        if elapsed_time >= max_wait_time:
            try:
                process.terminate()
                await asyncio.wait_for(process.wait(), timeout=5)
            except:
                try:
                    process.kill()
                except:
                    pass
            break
    
    # Récupérer les résultats
    try:
        return await process_task
    except:
        return -1, "", "Processus interrompu"

async def update_embed(interaction, match_id, is_modifiabled):
    # Récupération du nom du créateur
    response = supabase.table("Matchs").select("match_CreatorName").eq("match_ID", match_id).execute()
    
    CreatorName = ""
    if response.data and len(response.data) > 0:
        CreatorName = response.data[0]["match_CreatorName"]
    
    embed = discord.Embed(
        title="🎯 LA GAME VA BIENTOT COMMENCER !",
        description=f"**{CreatorName}** est le créateur de la partie !\nEn attente des autres joueurs...",
        color=discord.Color.blurple()
    )

    embed.add_field(name="EQUIPE BLEU :", value="🔹", inline=True)
    embed.add_field(name="EQUIPE ROUGE :", value="🔸", inline=True)

    embed.set_thumbnail(url="https://seek-team-prod.s3.fr-par.scw.cloud/users/67c758968e61a685175513.jpg")  # Ton URL

    # Vue et bouton "Quitter"
    quit_button = QuitButton()
    view = GameFreeActionButtons(quit_button)

    if is_modifiabled :
        asyncio.create_task(quit_button.start_countdown(interaction, match_id, is_modifiabled))

    # Envoie l'embed initial
    #await interaction.message.edit(embed=embed, view=view)
    
    # Récupération des noms des joueurs
    players_response = supabase.table("Matchs").select(
        "match_PlayerName_1, match_PlayerName_2, match_PlayerName_3, "
        "match_PlayerName_4, match_PlayerName_5, match_PlayerName_6, "
        "match_PlayerName_7, match_PlayerName_8, match_PlayerName_9, "
        "match_PlayerName_10"
    ).eq("match_ID", match_id).eq("match_Status", 1).execute()
    
    result = players_response.data[0] if players_response.data else None

    if result:
        players = [name for name in result.values() if name]  # filtre les None

        # Exemple simple : 5 joueurs par équipe
        blue_team = players[:5]
        red_team = players[5:]

        embed.set_field_at(0, name="EQUIPE BLEU :", value="🔹 " + '\n🔹 '.join(blue_team) if blue_team else "🔹", inline=True)
        embed.set_field_at(1, name="EQUIPE ROUGE :", value="🔸 " + '\n🔸 '.join(red_team) if red_team else "🔸", inline=True)

        await interaction.message.edit(embed=embed, view=view)

        # Récupération des messages liés
        linked_msgs_response = supabase.table("Matchs").select(
            "Linked_Embbeded_MSG_1, Linked_Embbeded_MSG_2, Linked_Embbeded_MSG_3, "
            "Linked_Embbeded_MSG_4, Linked_Embbeded_MSG_5, Linked_Embbeded_MSG_6, "
            "Linked_Embbeded_MSG_7, Linked_Embbeded_MSG_8, Linked_Embbeded_MSG_9, "
            "Linked_Embbeded_MSG_10"
        ).eq("match_ID", match_id).eq("match_Status", 1).execute()
        
        result = linked_msgs_response.data[0] if linked_msgs_response.data else None

        # Récupération du channel et message de l'hôte
        host_response = supabase.table("Matchs").select(
            "hosted_channelID, hosted_messageID"
        ).eq("match_ID", match_id).eq("match_Status", 1).execute()
        
        result2 = host_response.data[0] if host_response.data else None
            
        if result:
            data_listed = [data for data in result.values() if data]  # filtre les None
            for data_dict in data_listed :
                dict_data = json.loads(data_dict)
                channel = bot.get_channel(int(dict_data['channel_id']))
                message = await channel.fetch_message(int(dict_data['message_id']))
                if (str(dict_data['channel_id']) == str(result2['hosted_channelID'])) and (str(dict_data['message_id']) == str(result2['hosted_messageID'])) and (len(players) == 10) :
                    enabled_view = StartGameViewButtons(quit_button)
                    await message.edit(embed=embed, view = enabled_view)
                else:
                    await message.edit(embed=embed)

class QuitButton(discord.ui.Button):
    def __init__(self, countdown: int = 150):
        super().__init__(label=f"Quitter", style=discord.ButtonStyle.red, custom_id="leave_game")
        self.countdown = countdown
        self.message = None
        self.embed = None
        self.quit_triggered = False

    async def start_countdown(self, interaction: discord.Interaction, match_id, is_modifiabled):
        if match_id not in countdown_flags:
            countdown_flags[match_id] = {"done": False}
        
        self.message = interaction.message
        while self.countdown > 0:
            if countdown_flags[match_id]["done"]:
                break
            await asyncio.sleep(1)
            self.countdown -= 1

        if self.countdown <= 0:
            countdown_flags[match_id]["done"] = True
            
        # Mise à jour du statut du match
        supabase.table("Matchs").update({"match_Status": 3}).eq("match_ID", match_id).execute()
        
        cancel_embed = discord.Embed(
            title="⏱️ Partie annulée",
            description="Aucun joueur n'a rejoint à temps.",
            color=discord.Color.red()
        )
        try:
            await self.message.edit(embed=cancel_embed, view=None)  
        except (discord.NotFound, AttributeError):
            print("Impossible d'annuler : le message a été supprimé.")

        await asyncio.sleep(5)
        
        channel = interaction.message.channel

        # Récupération du type de licence
        licence_response = supabase.table("Licence").select("type_licence").eq(
            "Linked_discord_serverID", str(interaction.guild.id)
        ).gt("duree_validite_heure", 0).execute()
        
        result = licence_response.data[0] if licence_response.data else None
            
        if result :
        
            embed = discord.Embed(
                title=f'Offre **{result["type_licence"]}** active, lancer une partie dès maintenant !',
                description = f'Assurez-vous que tout les joueurs qui participeront sont dans le channel vocal : <#{channel.id}>',
                color=discord.Color.green()
            )
        view = StartFreeGameButton()
        if result["type_licence"] == "FREE" :
            view = StartFreeGameButton()
        if result["type_licence"] == "BASIC" :
            view = StartFreeGameButton()
        if result["type_licence"] == "EXPRESS" :
            view = StartGameButton()
        if result["type_licence"] == "PREMIUM" :
            view = StartGameButton()
            
        view = StartGameButton()
        
        await channel.purge(limit=None)
        
        if is_modifiabled : 
            if match_id in countdown_flags:
                del countdown_flags[match_id]
        
        await channel.send(embed=embed, view=view)

        
    async def callback(self, interaction: discord.Interaction):
        await interaction.response.defer()
        user_id = interaction.user.id

        

class StartGameViewButtons(discord.ui.View):
    def __init__(self, quit_button: QuitButton):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Rejoindre la partie", style=discord.ButtonStyle.blurple, custom_id="join_game"))
        self.add_item(discord.ui.Button(label="Lancer la partie", style=discord.ButtonStyle.green, disabled=False, custom_id="start_game"))
        self.add_item(quit_button)

class StartingServerViewButtons(discord.ui.View):
    def __init__(self, quit_button: QuitButton, countdown_seconds: int = 30):
        super().__init__(timeout=None)
        #self.add_item(discord.ui.Button(label="Rejoindre la partie", style=discord.ButtonStyle.blurple, custom_id="join_game"))
        self.add_item(discord.ui.Button(label=f"Démarrage du serveur ({countdown_seconds}s)", style=discord.ButtonStyle.green, disabled=True, custom_id="start_game"))
        #self.add_item(quit_button)

class ConnectServerViewButtons(discord.ui.View):
    def __init__(self, quit_button: QuitButton, server_ip: str = None):
        super().__init__(timeout=None)
        self.server_ip = server_ip
        #self.add_item(discord.ui.Button(label="Rejoindre la partie", style=discord.ButtonStyle.blurple, custom_id="join_game"))
        self.add_item(discord.ui.Button(label="Se connecter", style=discord.ButtonStyle.green, disabled=False, custom_id="connect_server"))
        #self.add_item(quit_button)

class GameFreeActionButtons(discord.ui.View):
    def __init__(self, quit_button: QuitButton):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Rejoindre la partie", style=discord.ButtonStyle.blurple, custom_id="join_game"))
        self.add_item(discord.ui.Button(label="Lancer la partie", style=discord.ButtonStyle.green, disabled=True, custom_id="start_game"))
        self.add_item(quit_button)
        
class StartGameButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Créer une partie publique", style=discord.ButtonStyle.green, custom_id="create_public_game"))
        self.add_item(discord.ui.Button(label="Créer une partie privée", style=discord.ButtonStyle.red, custom_id="create_private_game"))

class StartFreeGameButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(discord.ui.Button(label="Créer une partie publique", style=discord.ButtonStyle.green, custom_id="create_public_game"))
        
class VocalChannelSelect(discord.ui.Select):
    def __init__(self, channels: list[discord.VoiceChannel]):
        options = [
            discord.SelectOption(label=channel.name, value=str(channel.id))
            for channel in channels
        ]
        super().__init__(
            placeholder="Choisissez un salon vocal...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        channel_id = int(self.values[0])
        channel = interaction.guild.get_channel(channel_id)
        
        # Récupération du type de licence avec Supabase
        licence_response = supabase.table("Licence").select("type_licence").eq(
            "Linked_discord_serverID", str(interaction.guild.id)
        ).gt("duree_validite_heure", 0).execute()
        
        result = licence_response.data[0] if licence_response.data else None
            
        if result :
        
            embed = discord.Embed(
                title=f'Offre **{result["type_licence"]}** active, lancer une partie dès maintenant !',
                description = f'Assurez-vous que tout les joueurs qui participeront sont dans le channel vocal : <#{channel.id}>',
                color=discord.Color.green()
            )
        view = StartFreeGameButton()
        if result["type_licence"] == "FREE" :
            view = StartFreeGameButton()
        if result["type_licence"] == "BASIC" :
            view = StartFreeGameButton()
        if result["type_licence"] == "EXPRESS" :
            view = StartGameButton()
        if result["type_licence"] == "PREMIUM" :
            view = StartGameButton()
            
        view = StartGameButton()

        # Envoi de l'embed avec bouton dans le salon texte (car les salons vocaux ne supportent pas l'envoi de messages)
        try :
            await channel.purge(limit=None)
        except :
            pass
        
        await channel.send(embed=embed, view=view)

        await interaction.response.send_message(
            f"🎧 Salon vocal sélectionné : <#{channel_id}>", ephemeral=True
        )

class VocalChannelView(discord.ui.View):
    def __init__(self, channels: list[discord.VoiceChannel]):
        super().__init__(timeout=60)
        self.add_item(VocalChannelSelect(channels))

class CléModal(discord.ui.Modal, title="Enregistrer votre bot QuickFrag"):
    clé = discord.ui.TextInput(
        label="Veuillez entrer votre clé d'utilisation",
        placeholder="Ex: xxxx-xxxx-xxxx-xxxx",
        required=True,
        max_length=100,
    )

    async def on_submit(self, interaction: discord.Interaction):
        # Recherche de la licence avec Supabase
        licence_response = supabase.table("Licence").select("*").eq(
            "cle_licence", self.clé.value
        ).gt("duree_validite_heure", 0).execute()
        
        result = licence_response.data[0] if licence_response.data else None

        if result:
            # Mise à jour de la licence avec les informations du serveur
            supabase.table("Licence").update({
                "Linked_discord_serverName": interaction.guild.name,
                "Linked_discord_serverID": interaction.guild.id
            }).eq("cle_licence", self.clé.value).execute()
            
            # ✅ Clé correcte → on propose les salons vocaux
            voice_channels = [
                c for c in interaction.guild.voice_channels
            ]
            if not voice_channels:
                await interaction.response.send_message("Aucun salon vocal trouvé.", ephemeral=True)
                return

            view = VocalChannelView(voice_channels)
            await interaction.response.send_message(
                "✅ Clé correcte ! Sélectionne maintenant le salon vocal pour configurer les matchs :", 
                view=view, 
                ephemeral=True
            )
        else:
            # ❌ Clé incorrecte
            await interaction.response.send_message("❌ Clé incorrecte.", ephemeral=True)



# 🌐 Slash command /config
@bot.tree.command(name="config", description="Start the bot integrator configuration")
async def config(interaction: discord.Interaction):
    await interaction.response.send_modal(CléModal())

# 🔗 Slash command /link-steam (pour tester la liaison Steam)
@bot.tree.command(name="link-steam", description="Lier votre compte Steam à votre compte Discord")
async def link_steam(interaction: discord.Interaction):
    await interaction.response.defer(ephemeral=True)
    
    user_id = interaction.user.id
    
    # Vérifier si l'utilisateur a déjà un compte Steam lié
    player_steam_response = supabase.table("Players").select(
        "Steam_PlayerID"
    ).eq("Discord_PlayerID", str(user_id)).execute()
    
    if player_steam_response.data:
        steam_id = player_steam_response.data[0].get("Steam_PlayerID")
        if steam_id and str(steam_id).strip() and str(steam_id).strip() != "None":
            await interaction.followup.send(
                f"✅ Votre compte Steam est déjà lié ! (Steam ID: {steam_id})",
                ephemeral=True
            )
            return
    
    # Générer le lien d'authentification Steam
    auth_url, token = generate_steam_auth_url(user_id)
    
    embed = discord.Embed(
        title="🔗 Liaison compte Steam",
        description="Cliquez sur le lien ci-dessous pour lier votre compte Steam.",
        color=discord.Color.blue()
    )
    embed.add_field(
        name="📋 Instructions",
        value="1. Cliquez sur le lien ci-dessous\n"
              "2. Connectez-vous à votre compte Steam\n"
              "3. Autorisez la liaison\n"
              "4. Vous recevrez une confirmation par message privé",
        inline=False
    )
    embed.add_field(
        name="🔗 Lien de liaison Steam",
        value=f"[**Cliquer ici pour lier votre compte Steam**]({auth_url})",
        inline=False
    )
    embed.set_footer(text="Ce lien expire dans 30 minutes")
    
    await interaction.followup.send(embed=embed, ephemeral=True)

# 🔧 Slash command /steam-callback (pour simuler le callback Steam - à remplacer par un serveur web)
@bot.tree.command(name="steam-callback", description="[ADMIN] Traiter un callback Steam")
@app_commands.describe(
    token="Token de liaison",
    steam_id="Steam ID de l'utilisateur"
)
async def steam_callback_command(interaction: discord.Interaction, token: str, steam_id: str):
    await interaction.response.defer(ephemeral=True)
    
    # Simuler les paramètres de réponse Steam
    mock_steam_params = {
        "openid.identity": f"https://steamcommunity.com/openid/id/{steam_id}",
        "openid.mode": "id_res"
    }
    
    success, message = await handle_steam_callback(token, mock_steam_params)
    
    if success:
        await interaction.followup.send(f"✅ {message}", ephemeral=True)
    else:
        await interaction.followup.send(f"❌ {message}", ephemeral=True)
    
@bot.event
async def on_ready():
    await bot.tree.sync()
    await sync_all_emojis()
    print(f'We have logged in as {bot.user}')
    for guild in bot.guilds:
        print(f"Connecté à : {guild.name} (ID : {guild.id})")

    print("====== CONTEXTE D'EXÉCUTION ======")
    print(f"Utilisateur courant    : {getpass.getuser()}", flush=True)
    print(f"UID                    : {os.getuid() if hasattr(os, 'getuid') else 'N/A'}", flush=True)
    print(f"Chemin actuel          : {os.getcwd()}", flush=True)
    print(f"Fichier lancé          : {__file__}", flush=True)
    print(f"Arguments de lancement : {sys.argv}", flush=True)
    print(f"Système                : {platform.system()} {platform.release()}", flush=True)
    print(f"Python utilisé         : {sys.executable}", flush=True)
    print("==================================\n")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data.get("custom_id") == "leave_game":
            await interaction.response.defer()
        if interaction.data.get("custom_id") == "create_private_game":
            await interaction.response.defer()
            
            # Vérification du compte Steam lié pour le créateur
            if not await check_steam_link_required(interaction, "créer une partie privée"):
                return
        if interaction.data.get("custom_id") == "connect_server":
            channel = interaction.channel
            channel_id = channel.id
            user_joind_guild = interaction.guild.id
            
            # Recherche du match correspondant à ce message
            all_matches_response = supabase.table("Matchs").select("*").eq("match_Status", 2).execute()
            
            result = None
            if all_matches_response.data:
                for match in all_matches_response.data:
                    # Vérifier chaque champ de message lié
                    for i in range(1, 11):
                        msg_field = f"Linked_Embbeded_MSG_{i}"
                        if match.get(msg_field):
                            try:
                                msg_data = json.loads(match[msg_field])
                                if (str(msg_data.get('channel_id')) == str(channel_id) and 
                                    str(msg_data.get('message_id')) == str(interaction.message.id) and 
                                    str(msg_data.get('guild_id')) == str(user_joind_guild)):
                                    result = match
                                    break
                            except json.JSONDecodeError:
                                continue
                    if result:
                        break
            
            if result:
                match_id = result["match_ID"]
                
                # Récupération des informations du serveur
                server_response = supabase.table("ServersManager").select(
                    "server_IPAdress"
                ).eq("match_ID", match_id).eq("server_State", 2).execute()
                
                server_data = server_response.data[0] if server_response.data else None
                
                if server_data:
                    # Extraction de l'IP (enlever le port par défaut s'il existe)
                    server_ip = server_data["server_IPAdress"]
                    
                    embed = discord.Embed(
                        title="🎮 Connexion au serveur CS2",
                        description=f"**Copiez cette commande et collez-la dans votre console CS2 :**\n\n`connect {server_ip}`",
                        color=discord.Color.green()
                    )
                    embed.add_field(
                        name="📋 Instructions",
                        value="1. Ouvrez Counter-Strike 2\n2. Appuyez sur **`** (tilde) pour ouvrir la console\n3. Copiez-collez la commande ci-dessus\n4. Appuyez sur Entrée pour vous connecter",
                        inline=False
                    )
                    embed.add_field(
                        name="🔗 Commande de connexion",
                        value=f"```connect {server_ip}```",
                        inline=False
                    )
                    
                    await interaction.response.send_message(embed=embed, ephemeral=True)
                else:
                    await interaction.response.send_message("❌ Aucun serveur trouvé pour ce match.", ephemeral=True)
            else:
                await interaction.response.send_message("❌ Match non trouvé ou serveur non disponible.", ephemeral=True)
        if interaction.data.get("custom_id") == "start_game":
            list_mapName = ["de_ancient","de_anubis","de_dust2","de_inferno","de_mirage","de_nuke","de_overpass","de_train","de_vertigo"]
            channel = interaction.channel
            channel_id = channel.id
            user_joind_guild = interaction.guild.id
            #await interaction.response.defer()
            
            match_created = False
            # Récupération des serveurs disponibles
            servers_response = supabase.table("ServersManager").select(
                "server_State, match_ID, server_ID, server_IPAdress"
            ).eq("server_State", 1).execute()
            
            result = servers_response.data if servers_response.data else []
            if result :
                indexmatch = 0
                for row in result :
                    if row["match_ID"] == None :
                        match_created = True
                        break
                    indexmatch = indexmatch + 1

                # Recherche du match correspondant à ce message
                # Approche simplifiée : on récupère tous les matchs actifs et on vérifie les données JSON
                all_matches_response = supabase.table("Matchs").select("*").eq("match_Status", 1).execute()
                
                result3 = None
                if all_matches_response.data:
                    for match in all_matches_response.data:
                        # Vérifier chaque champ de message lié
                        for i in range(1, 11):
                            msg_field = f"Linked_Embbeded_MSG_{i}"
                            if match.get(msg_field):
                                try:
                                    msg_data = json.loads(match[msg_field])
                                    if (str(msg_data.get('channel_id')) == str(channel_id) and 
                                        str(msg_data.get('message_id')) == str(interaction.message.id) and 
                                        str(msg_data.get('guild_id')) == str(user_joind_guild)):
                                        result3 = match
                                        break
                                except json.JSONDecodeError:
                                    continue
                        if result3:
                            break

                if (result3) and (match_created == True) :
                    map_choiced = random.choice(list_mapName)
                    
                    PlayedMatchID = result3["match_ID"]
                    
                    # 1. MISE À JOUR DU STATUT DU MATCH
                    supabase.table("Matchs").update({"match_Status": 2}).eq("match_ID", PlayedMatchID).execute()
                    
                    # 2. RÉCUPÉRATION ET MISE À JOUR DES STEAMIDS AVANT LE REDÉMARRAGE
                    print(f"[INFO] Préparation de la whitelist pour le match {PlayedMatchID}")
                    
                    # Récupération des Discord_PlayerID des joueurs du match
                    match_players_response = supabase.table("Matchs").select(
                        "match_PlayerID_1, match_PlayerID_2, match_PlayerID_3, "
                        "match_PlayerID_4, match_PlayerID_5, match_PlayerID_6, "
                        "match_PlayerID_7, match_PlayerID_8, match_PlayerID_9, "
                        "match_PlayerID_10"
                    ).eq("match_ID", PlayedMatchID).execute()
                    
                    steam_ids_data = {}
                    # Réinitialiser toutes les colonnes à vide d'abord
                    for i in range(1, 11):
                        steam_ids_data[f"match_playersteam_{i}"] = ""
                    
                    if match_players_response.data:
                        match_data = match_players_response.data[0]
                        
                        # Pour chaque joueur, récupérer son SteamID depuis la table Players
                        for i in range(1, 11):
                            discord_player_id = match_data.get(f"match_PlayerID_{i}")
                            if discord_player_id:
                                # Récupération du SteamID depuis la table Players
                                player_steam_response = supabase.table("Players").select(
                                    "Steam_PlayerID"
                                ).eq("Discord_PlayerID", str(discord_player_id)).execute()
                                
                                if player_steam_response.data:
                                    steam_id = player_steam_response.data[0]["Steam_PlayerID"]
                                    if steam_id is not None:
                                        # Convertir en chaîne et nettoyer
                                        steam_id_str = str(steam_id).strip()
                                        if steam_id_str and steam_id_str != "None":
                                            steam_ids_data[f"match_playersteam_{i}"] = steam_id_str
                                            print(f"[DEBUG] Joueur {i} - Discord ID: {discord_player_id} -> Steam ID: {steam_id_str}")
                                        else:
                                            print(f"[WARNING] SteamID vide pour Discord ID: {discord_player_id}")
                                            steam_ids_data[f"match_playersteam_{i}"] = ""
                                    else:
                                        print(f"[WARNING] SteamID null pour Discord ID: {discord_player_id}")
                                        steam_ids_data[f"match_playersteam_{i}"] = ""
                                else:
                                    print(f"[WARNING] Aucun SteamID trouvé pour Discord ID: {discord_player_id}")
                                    steam_ids_data[f"match_playersteam_{i}"] = ""
                            else:
                                print(f"[DEBUG] Slot {i} vide - pas de joueur")
                                steam_ids_data[f"match_playersteam_{i}"] = ""
                    
                    # Mise à jour du serveur avec les SteamIDs AVANT le redémarrage
                    server_update_data = {
                        "match_ID": PlayedMatchID,
                        "server_State": 2,
                        "server_Map": map_choiced
                    }
                    
                    # Ajouter les SteamIDs récupérés
                    server_update_data.update(steam_ids_data)
                    
                    supabase.table("ServersManager").update(server_update_data).eq("server_ID", result[indexmatch]["server_ID"]).execute()
                    
                    print(f"[SUCCESS] Serveur mis à jour avec {len(steam_ids_data)} SteamIDs pour le match {PlayedMatchID}")
                    print(f"[INFO] Whitelist prête, démarrage du serveur CS2...")

                    # 3. PRÉPARATION DE LA COMMANDE SSH
                    sshadress = "ubuntu@"+str(result[indexmatch]["server_IPAdress"][:-6])
                    sshcommand = "sudo ./cs2_server_27016 " +map_choiced + " competitive restart"
                    ssh_key = "/root/.ssh/id_rsa_cs2"

                    ssh_command= ["ssh","-i",ssh_key,"-o","StrictHostKeyChecking=no",sshadress,sshcommand]

                    # 4. DÉMARRAGE DU COMPTE À REBOURS ET DE LA COMMANDE SSH
                    start_time = asyncio.get_event_loop().time()

                    await interaction.response.defer()
                    
                    # Mise à jour initiale de tous les messages liés avec le bouton de démarrage
                    await update_all_linked_messages_with_starting_server(PlayedMatchID, 60)
                    
                    # Exécution de la commande SSH avec mise à jour en temps réel
                    returncode, stdout, stderr = await update_server_countdown_real_time(PlayedMatchID, ssh_command, start_time)
                    
                    # Vérifier si le serveur a démarré avec succès
                    server_started = "*  The server has been started!  *" in stdout
                    
                    end_time = asyncio.get_event_loop().time()
                    elapsed_time = int(end_time - start_time)

                    # Mettre à jour tous les messages avec le bouton "Se connecter"
                    await update_all_linked_messages_with_connect_button(PlayedMatchID)
                    return
            await interaction.response.defer()
                

            
        if interaction.data.get("custom_id") == "join_game":
            await interaction.response.defer()
            user_joined_name = interaction.user.name
            user_joined_id = interaction.user.id
            user_joind_guild = interaction.guild.id

            # Vérification du compte Steam lié
            if not await check_steam_link_required(interaction, "rejoindre une partie"):
                return

            channel = interaction.channel
            channel_id = channel.id
            user_voice_connected = False
            
            for membre in channel.members :
                if interaction.user.id == membre.id :
                    user_voice_connected = True
                    break
                
            if user_voice_connected == False :
                await interaction.followup.send(
                    f"🎧 Vous devez vous connecter sur le channel vocal : <#{channel.id}>", ephemeral=True
                )
            else :
                # Recherche du match correspondant à ce message
                all_matches_response = supabase.table("Matchs").select("*").eq("match_Status", 1).execute()
                
                result = None
                if all_matches_response.data:
                    for match in all_matches_response.data:
                        # Vérifier chaque champ de message lié
                        for i in range(1, 11):
                            msg_field = f"Linked_Embbeded_MSG_{i}"
                            if match.get(msg_field):
                                try:
                                    msg_data = json.loads(match[msg_field])
                                    if (str(msg_data.get('channel_id')) == str(channel_id) and 
                                        str(msg_data.get('message_id')) == str(interaction.message.id) and 
                                        str(msg_data.get('guild_id')) == str(user_joind_guild)):
                                        result = match
                                        break
                                except json.JSONDecodeError:
                                    continue
                        if result:
                            break
                    
                if result :
                    team_picked = "BLUE"
                    
                    match_id = int(result["match_ID"])

                    # Récupération des équipes liées
                    team_response = supabase.table("Matchs").select(
                        "Linked_Channel_Team_1, Linked_Channel_Team_2, Linked_Channel_Team_3, "
                        "Linked_Channel_Team_4, Linked_Channel_Team_5, Linked_Channel_Team_6, "
                        "Linked_Channel_Team_7, Linked_Channel_Team_8, Linked_Channel_Team_9, "
                        "Linked_Channel_Team_10"
                    ).eq("match_ID", match_id).eq("match_Status", 1).execute()
                    
                    result2 = team_response.data[0] if team_response.data else None
                        
                    if result2 :
                        data_listed = [data for data in result2.values() if data]  # filtre les None
                        for data_dict in data_listed :
                            dict_data = json.loads(data_dict)
                            if str(dict_data['message_id']) == str(interaction.message.id) :
                                team_picked = dict_data['team_picked']

                        player_slots = []

                        if team_picked == "BLUE":
                            player_slots = [result.get(f"match_PlayerName_{i}") for i in range(1, 6)]
                        else :
                            if team_picked == "RED":
                                player_slots = [result.get(f"match_PlayerName_{i}") for i in range(6, 11)]
                                
                        filled_slots = sum(1 for slot in player_slots if slot is not None)
                        ids = 1
                        if filled_slots <= 4 :
                            if team_picked == "BLUE":
                                ids = filled_slots + 1
                            else :
                                if team_picked == "RED":
                                    ids = filled_slots + 6
                                    
                            # Mise à jour du joueur dans le match
                            update_data = {
                                f"match_PlayerName_{ids}": interaction.user.name,
                                f"match_PlayerID_{ids}": interaction.user.id
                            }
                            
                            supabase.table("Matchs").update(update_data).eq("match_ID", match_id).execute()

                            is_modifiabled = 0

                            await update_embed(interaction, match_id=match_id, is_modifiabled=is_modifiabled)
                            
                        else :
                            await interaction.followup.send(
                                f"❌ Equipe déjà complète, vous ne pouvez pas la rejoindre", ephemeral=True
                            )
                    
        if interaction.data.get("custom_id") == "create_public_game":
            await interaction.response.defer()
            
            # Vérification du compte Steam lié pour le créateur
            if not await check_steam_link_required(interaction, "créer une partie publique"):
                return

            is_modifiabled = 0

            channel = interaction.channel
            user_voice_connected = False
            for membre in channel.members :
                if interaction.user.id == membre.id :
                    user_voice_connected = True
                    break
            if len(channel.members) > 5 :
                await interaction.followup.send(
                    f"❌ Vous ne pouvez pas être plus de 5 joueurs lors de la création d'une partie", ephemeral=True
                )
                return
                
            if user_voice_connected == False :
                await interaction.followup.send(
                    f"🎧 Vous devez vous connecter sur le channel vocal : <#{channel.id}>", ephemeral=True
                )
                return
            else : 
                # Récupération des matchs publics existants
                public_matches_response = supabase.table("Matchs").select("*").eq("match_Status", 1).eq("private_party", False).execute()
                
                result = public_matches_response.data if public_matches_response.data else []
                
                if result :

                    available_members = [m for m in channel.members if not m.bot]
                    nb_actual_players = len(available_members)
                    
                    list_best_match_red = []
                    list_best_match_blue = []
                    
                    for row in result:
                        # On récupère les 5 slots joueurs RED dans une liste
                        player_slots = [row.get(f"match_PlayerName_{i}") for i in range(6, 11)]
                        filled_slots = sum(1 for slot in player_slots if slot is not None)
                        empty_slots = 5 - filled_slots

                        # Si la partie est complète, on ignore (0 signifie pas d'intérêt ici)
                        if empty_slots == 0:
                            list_best_match_red.append(0)
                            continue

                        # Si on peut compléter la partie avec les joueurs actuels, on donne un score max
                        if nb_actual_players >= empty_slots:
                            list_best_match_red.append(5)
                        else:
                            # On donne un score en fonction du nombre de joueurs qu'on peut ajouter
                            list_best_match_red.append(filled_slots + nb_actual_players)
                    
                    for row in result:
                        # On récupère les 5 slots joueurs BLUE dans une liste
                        player_slots = [row.get(f"match_PlayerName_{i}") for i in range(1, 6)]
                        filled_slots = sum(1 for slot in player_slots if slot is not None)
                        empty_slots = 5 - filled_slots

                        # Si la partie est complète, on ignore (0 signifie pas d'intérêt ici)
                        if empty_slots == 0:
                            list_best_match_blue.append(0)
                            continue

                        # Si on peut compléter la partie avec les joueurs actuels, on donne un score max
                        if nb_actual_players >= empty_slots:
                            list_best_match_blue.append(5)
                        else:
                            # On donne un score en fonction du nombre de joueurs qu'on peut ajouter
                            list_best_match_blue.append(filled_slots + nb_actual_players)

                    if (max(list_best_match_blue) > max(list_best_match_red)) :
                        best_index_blue = list_best_match_blue.index(max(list_best_match_blue))
                        best_match_row = result[best_index_blue]
                    else :
                        if (max(list_best_match_blue) < max(list_best_match_red)) :
                            best_index_red = list_best_match_red.index(max(list_best_match_red))
                            best_match_row = result[best_index_red]
                        else :
                            best_index_blue = list_best_match_blue.index(max(list_best_match_blue))
                            best_match_row = result[best_index_blue]

                    is_red_team = (max(list_best_match_red) >= max(list_best_match_blue))
                    
                    slots_to_fill = []
                    
                    if is_red_team:
                        id_slot_player = 6
                        for i in range(6, 11):
                            if best_match_row.get(f"match_PlayerName_{i}") is None:
                                slots_to_fill.append((f"match_PlayerName_{i}", f"match_PlayerID_{i}"))
                    else:
                        id_slot_player = 1
                        for i in range(1, 6):
                            if best_match_row.get(f"match_PlayerName_{i}") is None:
                                slots_to_fill.append((f"match_PlayerName_{i}", f"match_PlayerID_{i}"))

                    slots_to_fill = slots_to_fill[:len(available_members)]

                    # Préparation des données de mise à jour
                    update_data = {}
                    for (name_col, id_col), member in zip(slots_to_fill, available_members):
                        update_data[name_col] = member.name
                        update_data[id_col] = str(member.id)

                    match_id = best_match_row["match_ID"]
                    
                    # Mise à jour du match
                    supabase.table("Matchs").update(update_data).eq("match_ID", match_id).execute()
                    
                    # Récupération des messages liés existants
                    linked_msgs_response = supabase.table("Matchs").select(
                        "Linked_Embbeded_MSG_1, Linked_Embbeded_MSG_2, Linked_Embbeded_MSG_3, "
                        "Linked_Embbeded_MSG_4, Linked_Embbeded_MSG_5, Linked_Embbeded_MSG_6, "
                        "Linked_Embbeded_MSG_7, Linked_Embbeded_MSG_8, Linked_Embbeded_MSG_9, "
                        "Linked_Embbeded_MSG_10"
                    ).eq("match_ID", match_id).eq("match_Status", 1).execute()
                    
                    existing_msgs = linked_msgs_response.data[0] if linked_msgs_response.data else {}

                    len_List = 0
                    if existing_msgs:
                        len_List = sum(1 for i in range(1, 11) if existing_msgs.get(f"Linked_Embbeded_MSG_{i}"))
                        
                    # Ajout du nouveau message lié
                    data = {
                        "message_id" : interaction.message.id,
                        "channel_id" : interaction.channel.id,
                        "guild_id" : interaction.guild.id
                    }

                    serialized_data = json.dumps(data)

                    supabase.table("Matchs").update({
                        f"Linked_Embbeded_MSG_{len_List + 1}": serialized_data
                    }).eq("match_ID", match_id).execute()

                    # Ajout des informations d'équipe
                    team_data = {
                        "message_id" : interaction.message.id,
                        "team_picked" : "RED" if is_red_team else "BLUE"
                    }

                    team_serialized_data = json.dumps(team_data)

                    supabase.table("Matchs").update({
                        f"Linked_Channel_Team_{len_List + 1}": team_serialized_data
                    }).eq("match_ID", match_id).execute()

                    is_modifiabled = 1
                    
                else :
                    # Création d'un nouveau match
                    # Récupération du prochain ID de match
                    max_id_response = supabase.table("Matchs").select("match_ID").order("match_ID", desc=True).limit(1).execute()
                    match_id = (max_id_response.data[0]["match_ID"] + 1) if max_id_response.data else 1
                        
                    # Préparation des données du nouveau match
                    match_data = {
                        'match_ID': match_id,
                        'private_party': False,
                        'match_Offer_type': 'PREMIUM',
                        'match_Status': 1,
                        'match_CreatorName': interaction.user.name,
                        'hosted_server_discordName': interaction.guild.name,
                        'hosted_server_discordID': interaction.guild.id,
                        'hosted_channelID': interaction.channel.id,
                        'hosted_messageID': interaction.message.id
                    }

                    # Ajouter dynamiquement les colonnes des joueurs
                    for i, member in enumerate(channel.members, start=1):
                        match_data[f'match_PlayerName_{i}'] = member.name
                        match_data[f'match_PlayerID_{i}'] = member.id

                    # Insertion du nouveau match
                    supabase.table("Matchs").insert(match_data).execute()

                    # Ajout du message lié
                    data = {
                        "message_id" : interaction.message.id,
                        "channel_id" : interaction.channel.id,
                        "guild_id" : interaction.guild.id
                    }

                    serialized_data = json.dumps(data)

                    supabase.table("Matchs").update({
                        "Linked_Embbeded_MSG_1": serialized_data
                    }).eq("match_ID", match_id).execute()

                    # Ajout des informations d'équipe
                    team_data = {
                        "message_id" : interaction.message.id,
                        "team_picked" : "BLUE"
                    }

                    team_serialized_data = json.dumps(team_data)

                    supabase.table("Matchs").update({
                        "Linked_Channel_Team_1": team_serialized_data
                    }).eq("match_ID", match_id).execute()
                    
                    is_modifiabled = 1
                
                await update_embed(interaction, match_id=match_id, is_modifiabled=is_modifiabled)
                

bot.run(CLE_DISCORD)
