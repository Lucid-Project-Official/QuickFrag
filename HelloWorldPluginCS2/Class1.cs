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
        Console.WriteLine("=== PLUGIN QUICKFRAG WHITELIST DÉMARRAGE ===");
        Console.WriteLine($"Version: {ModuleVersion}");
        Console.WriteLine($"Auteur: {ModuleAuthor}");
        
        Server.NextFrame(() =>
        {
            Server.PrintToConsole("=== Plugin QuickFrag Whitelist chargé avec succès ===");
        });
        
        // Initialiser HttpClient
        httpClient = new HttpClient();
        httpClient.Timeout = TimeSpan.FromSeconds(30);
        Console.WriteLine("[INIT] HttpClient initialisé");
        
        // Obtenir l'adresse du serveur
        GetServerAddress();
        
        // Charger la whitelist depuis Supabase avec délai pour s'assurer que le serveur est prêt
        Console.WriteLine("[INIT] Programmation du chargement de la whitelist dans 5 secondes...");
        Task.Delay(5000).ContinueWith(_ => 
        {
            Console.WriteLine("[INIT] Début du chargement de la whitelist...");
            _ = LoadWhitelistFromDatabase();
        });
        
        // Enregistrer les événements
        RegisterEventHandler<EventPlayerConnectFull>(OnPlayerConnectFull);
        Console.WriteLine("[INIT] Événement PlayerConnectFull enregistré");
        
        Console.WriteLine("=== PLUGIN QUICKFRAG WHITELIST PRÊT ===");
    }

    private void GetServerAddress()
    {
        try
        {
            Console.WriteLine("[PORT] Diagnostic des variables de port du serveur CS2:");
            
            // Tester différentes variables de port
            var hostPort = ConVar.Find("hostport");
            var port = ConVar.Find("port");
            var ip = ConVar.Find("ip");
            var netPort = ConVar.Find("net_port");
            var hostName = ConVar.Find("hostname");
            
            Console.WriteLine($"[PORT] hostname: {hostName?.StringValue ?? "NULL"}");
            Console.WriteLine($"[PORT] hostport: {hostPort?.GetPrimitiveValue<int>() ?? -1} (existe: {hostPort != null})");
            Console.WriteLine($"[PORT] port: {port?.GetPrimitiveValue<int>() ?? -1} (existe: {port != null})");
            Console.WriteLine($"[PORT] ip: {ip?.StringValue ?? "NULL"}");
            Console.WriteLine($"[PORT] net_port: {netPort?.GetPrimitiveValue<int>() ?? -1} (existe: {netPort != null})");
            
            // Essayer de récupérer le bon port
            int serverPort = 27016; // Port par défaut
            
            // Prioriser les variables dans l'ordre de fiabilité
            if (hostPort != null)
            {
                serverPort = hostPort.GetPrimitiveValue<int>();
                Console.WriteLine($"[PORT] Utilisation de hostport: {serverPort}");
            }
            else if (port != null)
            {
                serverPort = port.GetPrimitiveValue<int>();
                Console.WriteLine($"[PORT] Utilisation de port: {serverPort}");
            }
            else if (netPort != null)
            {
                serverPort = netPort.GetPrimitiveValue<int>();
                Console.WriteLine($"[PORT] Utilisation de net_port: {serverPort}");
            }
            else
            {
                Console.WriteLine($"[PORT] Aucune variable trouvée, utilisation du port par défaut: {serverPort}");
            }
            
            // Si le port détecté est 27015, forcer 27016 selon votre configuration
            if (serverPort == 27015)
            {
                Console.WriteLine("[PORT] Port 27015 détecté, mais serveur configuré pour 27016 - correction appliquée");
                serverPort = 27016;
            }
            
            // Pour l'IP, nous devons utiliser une méthode alternative car CS2 ne donne pas directement l'IP publique
            string serverIp = "57.130.20.184"; // IP configurée manuellement
            
            serverAddress = $"{serverIp}:{serverPort}";
            Console.WriteLine($"[PORT] Adresse finale du serveur : {serverAddress}");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[ERROR] Erreur lors de la détection de l'adresse du serveur : {ex.Message}");
            serverAddress = "57.130.20.184:27016"; // Valeur par défaut sécurisée
            Console.WriteLine($"[PORT] Utilisation de l'adresse par défaut : {serverAddress}");
        }
    }

    private async Task LoadWhitelistFromDatabase()
    {
        Console.WriteLine("======== DÉBUT LOADWHITELISTFROMDATABASE ========");
        Console.WriteLine($"[TIMESTAMP] {DateTime.Now:yyyy-MM-dd HH:mm:ss}");
        
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
        finally
        {
            Console.WriteLine($"[FINAL] Whitelist finale: {whitelistedSteamIds.Count} entrées");
            Console.WriteLine("======== FIN LOADWHITELISTFROMDATABASE ========");
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

            Console.WriteLine($"[CONNECT] Nouvelle connexion détectée: {player.PlayerName}");
            
            // ÉTAPE 1: Recharger la whitelist pour avoir les données les plus récentes
            Console.WriteLine("[CONNECT] Rechargement de la whitelist pour être à jour...");
            
            // Charger la whitelist de manière synchrone pour ce joueur
            Task.Run(async () =>
            {
                await LoadWhitelistFromDatabase();
                
                // ÉTAPE 2: Après le rechargement, vérifier l'autorisation
                Server.NextFrame(() =>
                {
                    try
                    {
                        if (player == null || !player.IsValid || player.Connected != PlayerConnectedState.PlayerConnected)
                        {
                            Console.WriteLine("[CONNECT] Joueur déjà déconnecté, ignorer la vérification");
                            return;
                        }
                        
                        CheckPlayerAuthorization(player);
                    }
                    catch (Exception checkEx)
                    {
                        Console.WriteLine($"[ERROR] Erreur lors de la vérification d'autorisation: {checkEx.Message}");
                    }
                });
            });
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[CRITICAL] Erreur dans OnPlayerConnectFull: {ex.Message}");
            Console.WriteLine($"[CRITICAL] Stack trace: {ex.StackTrace}");
        }

        return HookResult.Continue;
    }
    
    private void CheckPlayerAuthorization(CCSPlayerController player)
    {
        try
        {
            // Récupérer différents formats de SteamID pour diagnostiquer
            string playerSteamId64 = player.SteamID.ToString();
            string playerAuthId = player.AuthorizedSteamID?.SteamId64.ToString() ?? "N/A";
            
            Console.WriteLine($"[AUTH] Vérification d'autorisation pour: {player.PlayerName}");
            Console.WriteLine($"[AUTH] SteamID (player.SteamID): {playerSteamId64}");
            Console.WriteLine($"[AUTH] AuthorizedSteamID: {playerAuthId}");
            Console.WriteLine($"[AUTH] Whitelist contient {whitelistedSteamIds.Count} entrées:");
            
            foreach (var whitelistedId in whitelistedSteamIds)
            {
                Console.WriteLine($"[AUTH] - Whitelist: '{whitelistedId}'");
            }
            
            // Tenter les différents formats pour la comparaison
            bool isAuthorized = whitelistedSteamIds.Contains(playerSteamId64) || 
                               whitelistedSteamIds.Contains(playerAuthId);
            
            Console.WriteLine($"[AUTH] Résultat autorisation: {isAuthorized}");
            
                         if (!isAuthorized)
             {
                 // Protection contre les reconnexions rapides
                 lock (kickLock)
                 {
                     if (recentlyKickedPlayers.Contains(playerSteamId64))
                     {
                         Console.WriteLine($"[WARNING] Joueur {player.PlayerName} déjà récemment kické - ignoré pour éviter le crash");
                         return;
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
                             
                             // Essayer différentes méthodes de kick
                             try
                             {
                                 // Méthode 1: Kick par nom (plus fiable)
                                 Server.ExecuteCommand($"kick \"{player.PlayerName}\" \"Vous ne pouvez pas rejoindre ce match.\"");
                                 Console.WriteLine($"[SUCCESS] Kick par nom exécuté pour {player.PlayerName}");
                             }
                             catch (Exception kickNameEx)
                             {
                                 Console.WriteLine($"[WARNING] Kick par nom échoué: {kickNameEx.Message}");
                                 
                                 try
                                 {
                                     // Méthode 2: Kick par UserID (fallback)
                                     Server.ExecuteCommand($"kickid {player.UserId} \"Vous ne pouvez pas rejoindre ce match.\"");
                                     Console.WriteLine($"[SUCCESS] Kick par UserID exécuté pour {player.PlayerName}");
                                 }
                                                                   catch (Exception kickIdEx)
                                  {
                                      Console.WriteLine($"[ERROR] Kick par UserID échoué: {kickIdEx.Message}");
                                      Console.WriteLine($"[WARNING] Toutes les méthodes de kick ont échoué pour {player.PlayerName}");
                                  }
                             }
                             
                             Console.WriteLine($"[SUCCESS] Joueur {player.PlayerName} (SteamID: {playerSteamId64}) traité - non autorisé");
                             
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
            Console.WriteLine($"[CRITICAL] Erreur dans CheckPlayerAuthorization: {ex.Message}");
            Console.WriteLine($"[CRITICAL] Stack trace: {ex.StackTrace}");
        }
    }

    // Commande pour recharger la whitelist manuellement
    [ConsoleCommand("css_reload_whitelist", "Recharge la whitelist depuis la base de données")]
    [CommandHelper(minArgs: 0, usage: "", whoCanExecute: CommandUsage.SERVER_ONLY)]
    public void OnReloadWhitelistCommand(CCSPlayerController? player, CommandInfo commandInfo)
    {
        Console.WriteLine("[MANUAL] Rechargement manuel de la whitelist demandé");
        _ = LoadWhitelistFromDatabase();
        commandInfo.ReplyToCommand("Rechargement de la whitelist en cours...");
    }

    // Commande pour afficher le statut de la whitelist
    [ConsoleCommand("css_whitelist_status", "Affiche le statut de la whitelist")]
    [CommandHelper(minArgs: 0, usage: "", whoCanExecute: CommandUsage.SERVER_ONLY)]
    public void OnWhitelistStatusCommand(CCSPlayerController? player, CommandInfo commandInfo)
    {
        Console.WriteLine($"[STATUS] Adresse du serveur: {serverAddress}");
        Console.WriteLine($"[STATUS] Nombre de joueurs autorisés: {whitelistedSteamIds.Count}");
        Console.WriteLine($"[STATUS] Liste des SteamIDs autorisés:");
        
        if (whitelistedSteamIds.Count == 0)
        {
            Console.WriteLine("[STATUS] - Aucun joueur autorisé (WHITELIST VIDE!)");
        }
        else
        {
            foreach (var steamId in whitelistedSteamIds)
            {
                Console.WriteLine($"[STATUS] - {steamId}");
            }
        }
        
        commandInfo.ReplyToCommand($"Whitelist: {whitelistedSteamIds.Count} joueurs autorisés");
    }

    public override void Unload(bool hotReload)
    {
        httpClient?.Dispose();
        Console.WriteLine("Plugin QuickFrag Whitelist déchargé !");
    }
}