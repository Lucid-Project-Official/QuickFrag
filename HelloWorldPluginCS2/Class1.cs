using CounterStrikeSharp.API;
using CounterStrikeSharp.API.Core;
using CounterStrikeSharp.API.Core.Attributes.Registration;
using CounterStrikeSharp.API.Modules.Commands;
using CounterStrikeSharp.API.Modules.Cvars;
using CounterStrikeSharp.API.Modules.Events;
using System.Text.Json;
using System.Net.Http;

namespace HelloWorldPluginCS2;

public class WhitelistPlugin : BasePlugin
{
    public override string ModuleName => "QuickFrag Whitelist";
    public override string ModuleVersion => "1.0.0";
    public override string ModuleAuthor => "Linoxyr";
    public override string ModuleDescription => "Plugin de whitelist dynamique pour CS2 avec Supabase";

    private HttpClient? httpClient;
    private string? serverAddress;
    private List<string> whitelistedSteamIds = new List<string>();
    private readonly HashSet<string> recentlyKickedPlayers = new HashSet<string>();
    private readonly object kickLock = new object();
    
    // Configuration Supabase - À MODIFIER avec vos vraies valeurs
    private const string SUPABASE_URL = "https://ifivxzwkkhwdbblgsbyo.supabase.co";
    private const string SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlmaXZ4endra2h3ZGJibGdzYnlvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTQ4OTc0MiwiZXhwIjoyMDY1MDY1NzQyfQ.C-9hO1SdaOVK2KtZfA1C4nBq1JkUO33OOu3icErgdH4";
    private const string TABLE_NAME = "ServersManager";

    public override void Load(bool hotReload)
    {
        Console.WriteLine("Plugin QuickFrag Whitelist chargé !");
        Server.PrintToConsole("Plugin de whitelist dynamique actif !");
        
        // Initialiser HttpClient
        httpClient = new HttpClient();
        httpClient.Timeout = TimeSpan.FromSeconds(30);
        
        // Obtenir l'adresse du serveur
        GetServerAddress();
        
        // Charger la whitelist depuis Supabase
        _ = LoadWhitelistFromDatabase();
        
        // Enregistrer les événements
        RegisterEventHandler<EventPlayerConnectFull>(OnPlayerConnectFull);
    }

    private void GetServerAddress()
    {
        try
        {
            // Récupérer l'IP et le port du serveur
            var hostName = ConVar.Find("hostname")?.StringValue ?? "Unknown";
            var serverPort = ConVar.Find("hostport")?.GetPrimitiveValue<int>() ?? 27016;
            
            // Pour l'IP, nous devons utiliser une méthode alternative car CS2 ne donne pas directement l'IP publique
            // Ici, nous utiliserons l'IP locale et le port pour l'exemple
            // Dans un environnement de production, vous devriez configurer l'IP publique manuellement
            string serverIp = "57.130.20.184"; // À remplacer par l'IP réelle du serveur
            
            serverAddress = $"{serverIp}:{serverPort}";
            Console.WriteLine($"Adresse du serveur détectée : {serverAddress}");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Erreur lors de la détection de l'adresse du serveur : {ex.Message}");
            serverAddress = "57.130.20.184:27016"; // Valeur par défaut
        }
    }

    private async Task LoadWhitelistFromDatabase()
    {
        try
        {
            Console.WriteLine("[DEBUG] Début de LoadWhitelistFromDatabase()");
            
            if (httpClient == null)
            {
                Console.WriteLine("[ERROR] HttpClient non initialisé");
                return;
            }

            if (string.IsNullOrEmpty(serverAddress))
            {
                Console.WriteLine("[ERROR] Adresse du serveur non disponible pour la recherche en base de données");
                return;
            }

            Console.WriteLine($"[DEBUG] Recherche pour le serveur : {serverAddress}");

            // Construire l'URL de l'API Supabase pour récupérer les données du serveur
            string url = $"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?server_IPAdress=eq.{serverAddress}&select=match_playersteam_1,match_playersteam_2,match_playersteam_3,match_playersteam_4,match_playersteam_5,match_playersteam_6,match_playersteam_7,match_playersteam_8,match_playersteam_9,match_playersteam_10";

            Console.WriteLine($"[DEBUG] URL construite : {url}");
            Console.WriteLine($"[DEBUG] URL Supabase : {SUPABASE_URL}");
            Console.WriteLine($"[DEBUG] Table : {TABLE_NAME}");

            httpClient.DefaultRequestHeaders.Clear();
            httpClient.DefaultRequestHeaders.Add("apikey", SUPABASE_ANON_KEY);
            httpClient.DefaultRequestHeaders.Add("Authorization", $"Bearer {SUPABASE_ANON_KEY}");

            Console.WriteLine("[DEBUG] Headers ajoutés, envoi de la requête...");

            HttpResponseMessage response = await httpClient.GetAsync(url);
            
            Console.WriteLine($"[DEBUG] Réponse reçue - Status Code: {response.StatusCode}");
            Console.WriteLine($"[DEBUG] Reason Phrase: {response.ReasonPhrase}");

            if (response.IsSuccessStatusCode)
            {
                string jsonResponse = await response.Content.ReadAsStringAsync();
                Console.WriteLine($"[DEBUG] Réponse JSON reçue : {jsonResponse}");
                
                using JsonDocument document = JsonDocument.Parse(jsonResponse);
                var serverDataArray = document.RootElement;

                Console.WriteLine($"[DEBUG] Nombre d'éléments dans la réponse : {serverDataArray.GetArrayLength()}");

                whitelistedSteamIds.Clear();

                if (serverDataArray.GetArrayLength() > 0)
                {
                    var server = serverDataArray[0];
                    Console.WriteLine("[DEBUG] Traitement du premier serveur trouvé");
                    
                    // Extraire tous les SteamIDs des colonnes match_playersteam_1 à match_playersteam_10
                    for (int i = 1; i <= 10; i++)
                    {
                        string columnName = $"match_playersteam_{i}";
                        if (server.TryGetProperty(columnName, out JsonElement steamIdElement))
                        {
                            string? steamId = steamIdElement.GetString()?.Trim();
                            if (!string.IsNullOrEmpty(steamId) && steamId != "null")
                            {
                                // Vérifier si le SteamID existe déjà pour éviter les doublons
                                if (!whitelistedSteamIds.Contains(steamId))
                                {
                                    whitelistedSteamIds.Add(steamId);
                                    Console.WriteLine($"[DEBUG] SteamID ajouté : {steamId} (colonne {columnName})");
                                }
                                else
                                {
                                    Console.WriteLine($"[WARNING] SteamID déjà présent : {steamId} (colonne {columnName}) - ignoré");
                                }
                            }
                        }
                    }

                    Console.WriteLine($"[SUCCESS] Whitelist chargée : {whitelistedSteamIds.Count} joueurs autorisés");
                    
                    // Utiliser Server.NextFrame pour exécuter sur le thread principal
                    int count = whitelistedSteamIds.Count;
                    Server.NextFrame(() =>
                    {
                        Server.PrintToConsole($"Whitelist mise à jour : {count} joueurs autorisés pour ce serveur");
                    });
                }
                else
                {
                    Console.WriteLine($"[WARNING] Aucune configuration trouvée pour le serveur {serverAddress}");
                }
            }
            else
            {
                string errorContent = await response.Content.ReadAsStringAsync();
                Console.WriteLine($"[ERROR] Erreur lors de la récupération des données");
                Console.WriteLine($"[ERROR] Status Code: {response.StatusCode}");
                Console.WriteLine($"[ERROR] Reason Phrase: {response.ReasonPhrase}");
                Console.WriteLine($"[ERROR] Contenu de l'erreur: {errorContent}");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[EXCEPTION] Erreur lors du chargement de la whitelist : {ex.Message}");
            Console.WriteLine($"[EXCEPTION] Stack Trace : {ex.StackTrace}");
        }
    }

    [GameEventHandler]
    public HookResult OnPlayerConnectFull(EventPlayerConnectFull @event, GameEventInfo info)
    {
        try
        {
            var player = @event.Userid;
            if (player == null || !player.IsValid)
                return HookResult.Continue;

            // Récupérer différents formats de SteamID pour diagnostiquer
            string playerSteamId64 = player.SteamID.ToString();
            string playerAuthId = player.AuthorizedSteamID?.SteamId64.ToString() ?? "N/A";
            
            Console.WriteLine($"[DEBUG] Connexion joueur: {player.PlayerName}");
            Console.WriteLine($"[DEBUG] SteamID (player.SteamID): {playerSteamId64}");
            Console.WriteLine($"[DEBUG] AuthorizedSteamID: {playerAuthId}");
            Console.WriteLine($"[DEBUG] Whitelist contient {whitelistedSteamIds.Count} entrées:");
            
            foreach (var whitelistedId in whitelistedSteamIds)
            {
                Console.WriteLine($"[DEBUG] - Whitelist: '{whitelistedId}'");
            }
            
            // Tenter les différents formats pour la comparaison
            bool isAuthorized = whitelistedSteamIds.Contains(playerSteamId64) || 
                               whitelistedSteamIds.Contains(playerAuthId);
            
            Console.WriteLine($"[DEBUG] Résultat autorisation: {isAuthorized}");
            
                         if (!isAuthorized)
             {
                 // Protection contre les reconnexions rapides
                 lock (kickLock)
                 {
                     if (recentlyKickedPlayers.Contains(playerSteamId64))
                     {
                         Console.WriteLine($"[WARNING] Joueur {player.PlayerName} déjà récemment kické - ignoré pour éviter le crash");
                         return HookResult.Continue;
                     }
                     
                     recentlyKickedPlayers.Add(playerSteamId64);
                 }
                 
                 Console.WriteLine($"[INFO] Joueur {player.PlayerName} non autorisé - préparation du kick");
                 
                 // Le joueur n'est pas autorisé, le kicker avec une approche plus sûre
                 Server.NextFrame(() =>
                 {
                     try
                     {
                         if (player != null && player.IsValid && player.Connected == PlayerConnectedState.PlayerConnected)
                         {
                             Console.WriteLine($"[INFO] Execution du kick pour {player.PlayerName}");
                             Server.ExecuteCommand($"kickid {player.UserId} \"Vous ne pouvez pas rejoindre ce match.\"");
                             Console.WriteLine($"[SUCCESS] Joueur {player.PlayerName} (SteamID: {playerSteamId64}) exclu - non autorisé");
                             
                             // Nettoyer après 10 secondes
                             Task.Delay(10000).ContinueWith(_ =>
                             {
                                 lock (kickLock)
                                 {
                                     recentlyKickedPlayers.Remove(playerSteamId64);
                                 }
                             });
                         }
                         else
                         {
                             Console.WriteLine($"[WARNING] Impossible de kicker - joueur déjà déconnecté");
                             lock (kickLock)
                             {
                                 recentlyKickedPlayers.Remove(playerSteamId64);
                             }
                         }
                     }
                     catch (Exception kickEx)
                     {
                         Console.WriteLine($"[ERROR] Erreur lors du kick: {kickEx.Message}");
                         lock (kickLock)
                         {
                             recentlyKickedPlayers.Remove(playerSteamId64);
                         }
                     }
                 });
             }
            else
            {
                Console.WriteLine($"[SUCCESS] Joueur {player.PlayerName} (SteamID: {playerSteamId64}) autorisé à rejoindre");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[CRITICAL] Erreur dans OnPlayerConnectFull: {ex.Message}");
            Console.WriteLine($"[CRITICAL] Stack trace: {ex.StackTrace}");
        }

        return HookResult.Continue;
    }

    // Commande pour recharger la whitelist manuellement
    [ConsoleCommand("css_reload_whitelist", "Recharge la whitelist depuis la base de données")]
    [CommandHelper(minArgs: 0, usage: "", whoCanExecute: CommandUsage.SERVER_ONLY)]
    public void OnReloadWhitelistCommand(CCSPlayerController? player, CommandInfo commandInfo)
    {
        _ = LoadWhitelistFromDatabase();
        commandInfo.ReplyToCommand("Rechargement de la whitelist en cours...");
    }

    public override void Unload(bool hotReload)
    {
        httpClient?.Dispose();
        Console.WriteLine("Plugin QuickFrag Whitelist déchargé !");
    }
}