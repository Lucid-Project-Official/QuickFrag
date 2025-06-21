import discord, asyncio, re, json, subprocess, random, os
from discord.ext import commands
from discord import app_commands
from supabase import create_client, Client
from pathlib import Path

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

CLE_DISCORD = os.getenv("DISCORD_TOKEN")

# Configuration Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_ANON_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


countdown_flags = {}

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
    
@bot.event
async def on_ready():
    await bot.tree.sync()
    print(f'We have logged in as {bot.user}')
    for guild in bot.guilds:
        print(f"Connecté à : {guild.name} (ID : {guild.id})")

@bot.event
async def on_interaction(interaction: discord.Interaction):
    if interaction.type == discord.InteractionType.component:
        if interaction.data.get("custom_id") == "leave_game":
            await interaction.response.defer()
        if interaction.data.get("custom_id") == "create_private_game":
            await interaction.response.defer()
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
                    
                    # Mise à jour du statut du match
                    supabase.table("Matchs").update({"match_Status": 2}).eq("match_ID", PlayedMatchID).execute()
                    
                    # Mise à jour du serveur
                    supabase.table("ServersManager").update({
                        "match_ID": PlayedMatchID,
                        "server_State": 2,
                        "server_Map": map_choiced
                    }).eq("server_ID", result[indexmatch]["server_ID"]).execute()

                    sshadress = "ubuntu@"+str(result[indexmatch]["server_IPAdress"][:-6])
                    sshcommand = "sudo ./cs2_server_27016 " +map_choiced + " competitive restart"
                    ssh_key = "/root/.ssh/id_rsa_cs2"

                    print(sshadress)

                    ssh_command= ["ssh","-i",ssh_key,"-o","StrictHostKeyChecking=no",sshadress,sshcommand]

                    resultatssh = subprocess.run(ssh_command, capture_output=True, text=True)

                    print(resultatssh.stdout)
                    print(resultatssh.stderr)

                    message = str(sshadress) + "\n" + str(resultatssh.stderr) + "\n" + str(resultatssh.stdout)
                    
                    await interaction.response.send_message("Vous avez lancé la partie. " + message, ephemeral=True)
            await interaction.response.defer()
                

            
        if interaction.data.get("custom_id") == "join_game":
            await interaction.response.defer()
            user_joined_name = interaction.user.name
            user_joined_id = interaction.user.id
            user_joind_guild = interaction.guild.id

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
                
            if user_voice_connected == False :
                await interaction.followup.send(
                    f"🎧 Vous devez vous connecter sur le channel vocal : <#{channel.id}>", ephemeral=True
                )
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
