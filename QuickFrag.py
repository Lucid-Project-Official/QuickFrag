import discord, psycopg2, asyncio, re, json, subprocess, random, os
from discord.ext import commands
from discord import app_commands

intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

#CLE_DE_CONNECTION = "postgres://avnadmin:AG5atjsOPUcdH1X364mT@postgresql-e571afbf-oc67a9097.database.cloud.ovh.net:20184/QuickFrag?sslmode=require"
#DISCORD_TOKEN = "MTM1ODgyODI5ODIzODQzMTQ1Mw.Gk5S_p._XH6BOLX4EHFy8gQriyxI-sXo-3fwEvxkqjuMY"
CLE_DE_CONNECTION = os.getenv("OVHCLOUD_TOKEN")
CLE_DISCORD = os.getenv("DISCORD_TOKEN")

countdown_flags = {}

async def update_embed(interaction, match_id, is_modifiabled):
    connection = psycopg2.connect(CLE_DE_CONNECTION)
    cursor = connection.cursor()

    CreatorName = ""
    
    with connection.cursor() as cur:
        cur.execute("""
            SELECT match_CreatorName FROM Matchs
            WHERE match_ID = %s
        """,(match_id,))

        CreatorName = cur.fetchone()[0]
    
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
    
    with connection.cursor() as cur:
        cur.execute("""
            SELECT 
                match_PlayerName_1, match_PlayerName_2, match_PlayerName_3, 
                match_PlayerName_4, match_PlayerName_5, match_PlayerName_6,
                match_PlayerName_7, match_PlayerName_8, match_PlayerName_9, 
                match_PlayerName_10
            FROM Matchs WHERE match_ID = %s AND match_Status = 1
        """, (match_id,))
        result = cur.fetchone()

    if result:
        players = [name for name in result if name]  # filtre les None

        # Exemple simple : 5 joueurs par équipe
        blue_team = players[:5]
        red_team = players[5:]

        embed.set_field_at(0, name="EQUIPE BLEU :", value="🔹 " + '\n🔹 '.join(blue_team) if blue_team else "🔹", inline=True)
        embed.set_field_at(1, name="EQUIPE ROUGE :", value="🔸 " + '\n🔸 '.join(red_team) if red_team else "🔸", inline=True)

        await interaction.message.edit(embed=embed, view=view)

        with connection.cursor() as cur:
            cur.execute("""
                SELECT 
                    Linked_Embbeded_MSG_1, Linked_Embbeded_MSG_2, Linked_Embbeded_MSG_3, 
                    Linked_Embbeded_MSG_4, Linked_Embbeded_MSG_5, Linked_Embbeded_MSG_6,
                    Linked_Embbeded_MSG_7, Linked_Embbeded_MSG_8, Linked_Embbeded_MSG_9, 
                    Linked_Embbeded_MSG_10
                FROM Matchs WHERE match_ID = %s AND match_Status = 1
            """, (match_id,))
            result = cur.fetchone()

        with connection.cursor() as cur:
            cur.execute("""
                SELECT 
                    hosted_channelID, hosted_messageID
                FROM Matchs WHERE match_ID = %s AND match_Status = 1
            """, (match_id,))
            result2 = cur.fetchone()
            
        if result:
            data_listed = [data for data in result if data]  # filtre les None
            for data_dict in data_listed :
                dict_data = json.loads(data_dict)
                channel = bot.get_channel(int(dict_data['channel_id']))
                message = await channel.fetch_message(int(dict_data['message_id']))
                if (str(dict_data['channel_id']) == str(result2[0])) and (str(dict_data['message_id']) == str(result2[1])) and (len(players) == 10) :
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
        
        connection = psycopg2.connect(CLE_DE_CONNECTION)
        cursor = connection.cursor()
        
        self.message = interaction.message
        while self.countdown > 0:
            if countdown_flags[match_id]["done"]:
                break
            await asyncio.sleep(1)
            self.countdown -= 1

        if self.countdown <= 0:
            countdown_flags[match_id]["done"] = True
            
        with connection.cursor() as cur:
            cur.execute("""
                UPDATE Matchs
                SET match_Status = 3
                WHERE match_ID = %s
            """, (match_id,))
        connection.commit()
        
        cancel_embed = discord.Embed(
            title="⏱️ Partie annulée",
            description="Aucun joueur n'a rejoint à temps.",
            color=discord.Color.red()
        )
        try:
            await self.message.edit(embed=cancel_embed, view=None)  
        except (discord.NotFound, AttributeError):
            print("Impossible d’annuler : le message a été supprimé.")

        await asyncio.sleep(5)
        
        channel = interaction.message.channel

        connection = psycopg2.connect(CLE_DE_CONNECTION)
        cursor = connection.cursor()

        result = None

        with connection.cursor() as cur:
            cur.execute("""
                SELECT type_licence FROM Licence
                WHERE Linked_discord_serverID = %s AND duree_validite_heure > 0
            """, (str(interaction.guild.id),))

            result = cur.fetchone()
            
        if result :
        
            embed = discord.Embed(
                title=f'Offre **{result[0]}** active, lancer une partie dès maintenant !',
                description = f'Assurez-vous que tout les joueurs qui participeront sont dans le channel vocal : <#{channel.id}>',
                color=discord.Color.green()
            )
        view = StartFreeGameButton()
        if result[0] == "FREE" :
            view = StartFreeGameButton()
        if result[0] == "BASIC" :
            view = StartFreeGameButton()
        if result[0] == "EXPRESS" :
            view = StartGameButton()
        if result[0] == "PREMIUM" :
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
        
        connection = psycopg2.connect(CLE_DE_CONNECTION)
        cursor = connection.cursor()

        result = None

        with connection.cursor() as cur:
            cur.execute("""
                SELECT type_licence FROM Licence
                WHERE Linked_discord_serverID = %s AND duree_validite_heure > 0
            """, (str(interaction.guild.id),))

            result = cur.fetchone()
            
        if result :
        
            embed = discord.Embed(
                title=f'Offre **{result[0]}** active, lancer une partie dès maintenant !',
                description = f'Assurez-vous que tout les joueurs qui participeront sont dans le channel vocal : <#{channel.id}>',
                color=discord.Color.green()
            )
        view = StartFreeGameButton()
        if result[0] == "FREE" :
            view = StartFreeGameButton()
        if result[0] == "BASIC" :
            view = StartFreeGameButton()
        if result[0] == "EXPRESS" :
            view = StartGameButton()
        if result[0] == "PREMIUM" :
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
        connection = psycopg2.connect(CLE_DE_CONNECTION)
        cursor = connection.cursor()
        result = None

        with connection.cursor() as cur:
            cur.execute("""
                SELECT * FROM Licence
                WHERE cle_licence = %s AND duree_validite_heure > 0
            """, (self.clé.value,))

            result = cur.fetchone()

        if result:
            with connection.cursor() as cur:
                cur.execute("""
                    UPDATE Licence
                    SET Linked_discord_serverName = %s,
                        Linked_discord_serverID = %s
                    WHERE cle_licence = %s
                """, (interaction.guild.name, interaction.guild.id,self.clé.value))
            connection.commit()
            
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
            
            connection = psycopg2.connect(CLE_DE_CONNECTION)
            cursor = connection.cursor()
            match_created = False
            result = None
            with connection.cursor() as cur:
                cur.execute("""
                    SELECT server_State, match_ID, server_ID, server_IPAdress
                    FROM ServersManager WHERE server_State = 1
                """)
                result = cur.fetchall()
            if result :
                indexmatch = 0
                for row in result :
                    if row[1] == None :
                        match_created = True
                        break
                    indexmatch = indexmatch + 1

                result3 = None
                with connection.cursor() as cur:
                    params = [str(channel_id), str(interaction.message.id), str(user_joind_guild)] * 10

                    sql = """
                    SELECT * FROM Matchs
                    WHERE match_Status = 1 AND (
                        (Linked_Embbeded_MSG_1 IS NOT NULL AND
                         (Linked_Embbeded_MSG_1::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_1::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_1::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_2 IS NOT NULL AND
                         (Linked_Embbeded_MSG_2::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_2::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_2::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_3 IS NOT NULL AND
                         (Linked_Embbeded_MSG_3::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_3::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_3::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_4 IS NOT NULL AND
                         (Linked_Embbeded_MSG_4::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_4::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_4::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_5 IS NOT NULL AND
                         (Linked_Embbeded_MSG_5::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_5::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_5::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_6 IS NOT NULL AND
                         (Linked_Embbeded_MSG_6::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_6::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_6::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_7 IS NOT NULL AND
                         (Linked_Embbeded_MSG_7::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_7::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_7::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_8 IS NOT NULL AND
                         (Linked_Embbeded_MSG_8::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_8::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_8::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_9 IS NOT NULL AND
                         (Linked_Embbeded_MSG_9::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_9::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_9::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_10 IS NOT NULL AND
                         (Linked_Embbeded_MSG_10::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_10::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_10::json->>'guild_id') = %s)
                    )
                    """

                    cur.execute(sql, params)
                    result3 = cur.fetchone()
                if (result3) and  (match_created == True) :
                    map_choiced = random.choice(list_mapName)
                    
                    PlayedMatchID = result3[1]
                    with connection.cursor() as cur:
                        cur.execute("""
                                UPDATE Matchs
                                SET match_Status = 2
                                WHERE match_ID = %s
                            """, (PlayedMatchID,))
                    connection.commit()
                    with connection.cursor() as cur:
                        cur.execute("""
                                UPDATE ServersManager
                                SET match_ID = %s,
                                    server_State = 2,
                                    server_Map = %s
                                WHERE server_ID = %s
                            """, (PlayedMatchID,map_choiced,result[indexmatch][2],))
                    connection.commit()

                    sshadress = "ubuntu@"+str(result[indexmatch][3][:-6])
                    sshcommand = "sudo ./cs2_server_27016 " +map_choiced + " competitive restart" 
                    print(sshadress)

                    ssh_command= ["ssh","-i","/home/root/.ssh/id_rsa_cs2","-o","StrictHostKeyChecking=no",sshadress,sshcommand]

                    resultatssh = subprocess.run(ssh_command, capture_output=True, text=True)

                    print(resultatssh.stdout)
                    print(resultatssh.stderr)
                    
                    await interaction.response.send_message("Vous avez lancé la partie.", ephemeral=True)
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
                connection = psycopg2.connect(CLE_DE_CONNECTION)
                cursor = connection.cursor()
                result = None
                with connection.cursor() as cur:
                    

                    params = [str(channel_id), str(interaction.message.id), str(user_joind_guild)] * 10

                    sql = """
                    SELECT * FROM Matchs
                    WHERE match_Status = 1 AND (
                        (Linked_Embbeded_MSG_1 IS NOT NULL AND
                         (Linked_Embbeded_MSG_1::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_1::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_1::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_2 IS NOT NULL AND
                         (Linked_Embbeded_MSG_2::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_2::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_2::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_3 IS NOT NULL AND
                         (Linked_Embbeded_MSG_3::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_3::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_3::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_4 IS NOT NULL AND
                         (Linked_Embbeded_MSG_4::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_4::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_4::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_5 IS NOT NULL AND
                         (Linked_Embbeded_MSG_5::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_5::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_5::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_6 IS NOT NULL AND
                         (Linked_Embbeded_MSG_6::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_6::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_6::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_7 IS NOT NULL AND
                         (Linked_Embbeded_MSG_7::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_7::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_7::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_8 IS NOT NULL AND
                         (Linked_Embbeded_MSG_8::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_8::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_8::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_9 IS NOT NULL AND
                         (Linked_Embbeded_MSG_9::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_9::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_9::json->>'guild_id') = %s)
                     OR
                        (Linked_Embbeded_MSG_10 IS NOT NULL AND
                         (Linked_Embbeded_MSG_10::json->>'channel_id') = %s AND
                         (Linked_Embbeded_MSG_10::json->>'message_id') = %s AND
                         (Linked_Embbeded_MSG_10::json->>'guild_id') = %s)
                    )
                    """

                    cur.execute(sql, params)
                    result = cur.fetchone()
                    
                if result :
                    team_picked = "BLUE"
                    
                    match_id = int(result[1])

                    with connection.cursor() as cur:
                        cur.execute("""
                            SELECT 
                                Linked_Channel_Team_1, Linked_Channel_Team_2, Linked_Channel_Team_3, 
                                Linked_Channel_Team_4, Linked_Channel_Team_5, Linked_Channel_Team_6,
                                Linked_Channel_Team_7, Linked_Channel_Team_8, Linked_Channel_Team_9, 
                                Linked_Channel_Team_10
                            FROM Matchs WHERE match_ID = %s AND match_Status = 1
                        """, (match_id,))
                        result2 = cur.fetchone()
                        
                    if result2 :
                        data_listed = [data for data in result2 if data]  # filtre les None
                        for data_dict in data_listed :
                            dict_data = json.loads(data_dict)
                            if str(dict_data['message_id']) == str(interaction.message.id) :
                                team_picked = dict_data['team_picked']

                        player_slots = []

                        if team_picked == "BLUE":
                            player_slots = [result[6], result[8], result[10], result[12], result[14]]
                        else :
                            if team_picked == "RED":
                                player_slots = [result[16], result[18], result[20], result[22], result[24]]
                                
                        filled_slots = sum(1 for slot in player_slots if slot is not None)
                        ids = 1
                        if filled_slots <= 4 :
                            if team_picked == "BLUE":
                                ids = filled_slots + 1
                            else :
                                if team_picked == "RED":
                                    ids = filled_slots + 6
                                    
                            col_name = f"match_PlayerName_{ids}"
                            col_id = f"match_PlayerID_{ids}"

                            with connection.cursor() as cur:
                                cur.execute(f"""
                                    UPDATE Matchs
                                    SET {col_name} = %s,
                                        {col_id} = %s
                                    WHERE match_ID = %s
                                """, (interaction.user.name, interaction.user.id, match_id,))
                            connection.commit()

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

                connection = psycopg2.connect(CLE_DE_CONNECTION)
                cursor = connection.cursor()

                result = None

                with connection.cursor() as cur:
                    cur.execute("""
                        SELECT * FROM Matchs
                        WHERE match_Status = 1 AND private_party = FALSE
                    """)

                    result = cur.fetchall()
                if result :

                    available_members = [m for m in channel.members if not m.bot]
                    nb_actual_players = len(available_members)
                    
                    list_best_match_red = []
                    list_best_match_blue = []
                    
                    for row in result:
                        # On récupère les 5 slots joueurs dans une liste
                        player_slots = [row[16], row[18], row[20], row[22], row[24]]
                        filled_slots = sum(1 for slot in player_slots if slot is not None)
                        empty_slots = 5 - filled_slots

                        # Si la partie est complète, on ignore (0 signifie pas d’intérêt ici)
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
                        # On récupère les 5 slots joueurs dans une liste
                        player_slots = [row[6], row[8], row[10], row[12], row[14]]
                        filled_slots = sum(1 for slot in player_slots if slot is not None)
                        empty_slots = 5 - filled_slots

                        # Si la partie est complète, on ignore (0 signifie pas d’intérêt ici)
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
                    
                    if is_red_team:
                        slot_start_index = 16
                    else:
                        slot_start_index = 6

                    slots_to_fill = []
                    
                    if slot_start_index == 6 :
                        id_slot_player = 1
                    else :
                        id_slot_player = 6
                        
                    for i in range(5):
                        name_col_index = slot_start_index + i * 2
                        if best_match_row[name_col_index] is None:
                            slots_to_fill.append((f"match_PlayerName_{id_slot_player}", f"match_PlayerID_{id_slot_player}"))
                        id_slot_player = id_slot_player + 1

                    slots_to_fill = slots_to_fill[:len(available_members)]

                    set_parts = []
                    values = []

                    for (name_col, id_col), member in zip(slots_to_fill, available_members):
                        set_parts.append(f"{name_col} = %s, {id_col} = %s")
                        values.extend([member.name, str(member.id)])

                    set_clause = ", ".join(set_parts)

                    # Ajout de la clause WHERE avec l'ID du match
                    match_id = best_match_row[1]  # À adapter si match_ID n'est pas à l’index 0
                    values.append(match_id)

                    # Requête SQL finale
                    query = f"""
                        UPDATE Matchs
                        SET {set_clause}
                        WHERE match_ID = %s
                    """
                    with connection.cursor() as cur:
                        cur.execute(query, values)
                    connection.commit()
                    
                    with connection.cursor() as cur:
                        cur.execute("""
                            SELECT 
                                Linked_Embbeded_MSG_1, Linked_Embbeded_MSG_2, Linked_Embbeded_MSG_3, 
                                Linked_Embbeded_MSG_4, Linked_Embbeded_MSG_5, Linked_Embbeded_MSG_6,
                                Linked_Embbeded_MSG_7, Linked_Embbeded_MSG_8, Linked_Embbeded_MSG_9, 
                                Linked_Embbeded_MSG_10
                            FROM Matchs WHERE match_ID = %s AND match_Status = 1
                        """, (match_id,))
                        result = cur.fetchone()

                    len_List = 0
                    
                    if result:
                        len_List = len([data for data in result if data])
                        
                    # Exécution SQL
                    with connection.cursor() as cur:

                        data = {
                            "message_id" : interaction.message.id,
                            "channel_id" : interaction.channel.id,
                            "guild_id" : interaction.guild.id
                        }

                        serialized_data = json.dumps(data)

                        cur.execute("""
                            UPDATE Matchs
                            SET Linked_Embbeded_MSG_%s = %s
                            WHERE match_ID = %s
                        """, (len_List + 1, serialized_data, match_id,))
                        
                    connection.commit()

                    with connection.cursor() as cur:
                        cur.execute("""
                            SELECT 
                                Linked_Channel_Team_1, Linked_Channel_Team_2, Linked_Channel_Team_3, 
                                Linked_Channel_Team_4, Linked_Channel_Team_5, Linked_Channel_Team_6,
                                Linked_Channel_Team_7, Linked_Channel_Team_8, Linked_Channel_Team_9, 
                                Linked_Channel_Team_10
                            FROM Matchs WHERE match_ID = %s AND match_Status = 1
                        """, (match_id,))
                        result = cur.fetchone()

                    len_List = 0
                    
                    if result:
                        len_List = len([data for data in result if data])
                        
                    # Exécution SQL
                    team_picked = "BLUE"
                    
                    with connection.cursor() as cur:
    
                        if is_red_team :
                            team_picked = "RED"
                        else :
                            team_picked = "BLUE"
                            
                        data = {
                            "message_id" : interaction.message.id,
                            "team_picked" : team_picked
                        }

                        serialized_data = json.dumps(data)

                        cur.execute("""
                            UPDATE Matchs
                            SET Linked_Channel_Team_%s = %s
                            WHERE match_ID = %s
                        """, (len_List + 1, serialized_data, match_id,))
                        
                    connection.commit()

                    is_modifiabled = 1
                    
                else :
                    with connection.cursor() as cur:
                        cur.execute("""SELECT COALESCE(MAX(match_ID), 0) FROM Matchs""")
                        match_id = cur.fetchone()[0] + 1
                        
                        columns = [
                            'match_ID', 'private_party', 'match_Offer_type', 'match_Status',
                            'match_CreatorName', 'hosted_server_discordName', 'hosted_server_discordID', 'hosted_channelID','hosted_messageID'
                        ]
                        values = [
                            match_id, False, 'PREMIUM', 1,
                            interaction.user.name, interaction.guild.name, interaction.guild.id, interaction.channel.id, interaction.message.id
                        ]

                        # Ajouter dynamiquement les colonnes des joueurs
                        for i, member in enumerate(channel.members, start=1):
                            columns.append(f'match_PlayerName_{i}')
                            columns.append(f'match_PlayerID_{i}')
                            values.append(member.name)
                            values.append(member.id)

                        # Construction dynamique de la requête
                        placeholders = ', '.join(['%s'] * len(values))
                        columns_str = ', '.join(columns)

                        query = f"""
                            INSERT INTO Matchs ({columns_str})
                            VALUES ({placeholders})
                        """

                        cur.execute(query, values)

                        data = {
                            "message_id" : interaction.message.id,
                            "channel_id" : interaction.channel.id,
                            "guild_id" : interaction.guild.id
                        }

                        serialized_data = json.dumps(data)

                        cur.execute("""
                            UPDATE Matchs
                            SET Linked_Embbeded_MSG_1 = %s
                            WHERE match_ID = %s
                        """, (serialized_data, match_id,))
                    connection.commit()

                    with connection.cursor() as cur:

                        team_picked = "BLUE"
                            
                        data = {
                            "message_id" : interaction.message.id,
                            "team_picked" : team_picked
                        }

                        serialized_data = json.dumps(data)

                        cur.execute("""
                            UPDATE Matchs
                            SET Linked_Channel_Team_1 = %s
                            WHERE match_ID = %s
                        """, (serialized_data, match_id,))
                        
                    connection.commit()
                    
                    is_modifiabled = 1
                
                await update_embed(interaction, match_id=match_id, is_modifiabled=is_modifiabled)
                

bot.run(CLE_DISCORD)
