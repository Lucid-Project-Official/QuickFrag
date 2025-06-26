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
    private bool whitelistEnabled = true;
    private DateTime lastWhitelistReload = DateTime.MinValue;
    private bool isReloadingWhitelist = false;
    
    // Configuration Supabase - À MODIFIER avec vos vraies valeurs
    private const string SUPABASE_URL = "https://ifivxzwkkhwdbblgsbyo.supabase.co";
    private const string SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImlmaXZ4endra2h3ZGJibGdzYnlvIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0OTQ4OTc0MiwiZXhwIjoyMDY1MDY1NzQyfQ.C-9hO1SdaOVK2KtZfA1C4nBq1JkUO33OOu3icErgdH4";
    private const string TABLE_NAME = "ServersManager";

    public override void Load(bool hotReload)
    {
        Console.WriteLine("[PLUGIN] QuickFrag Whitelist v" + ModuleVersion + " - Démarrage");
        
        httpClient = new HttpClient();
        httpClient.Timeout = TimeSpan.FromSeconds(30);
        
        GetServerAddress();
        
        Task.Delay(3000).ContinueWith(_ => 
        {
            _ = LoadWhitelistFromDatabase();
        });
        
        RegisterEventHandler<EventPlayerConnectFull>(OnPlayerConnectFull);
        
        Console.WriteLine("[PLUGIN] QuickFrag Whitelist prêt");
    }



    private void GetServerAddress()
    {
        try
        {
            var hostPort = ConVar.Find("hostport");
            var port = ConVar.Find("port");
            var netPort = ConVar.Find("net_port");
            
            int serverPort = 27016; // Port par défaut
            
            if (hostPort != null)
                serverPort = hostPort.GetPrimitiveValue<int>();
            else if (port != null)
                serverPort = port.GetPrimitiveValue<int>();
            else if (netPort != null)
                serverPort = netPort.GetPrimitiveValue<int>();
            
            // Si le port détecté est 27015, forcer 27016
            if (serverPort == 27015)
                serverPort = 27016;
            
            string serverIp = "57.130.20.184";
            serverAddress = $"{serverIp}:{serverPort}";
            Console.WriteLine($"[CONFIG] Serveur: {serverAddress}");
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[ERROR] Port: {ex.Message}");
            serverAddress = "57.130.20.184:27016";
            Console.WriteLine($"[CONFIG] Serveur par défaut: {serverAddress}");
        }
    }

    private async Task LoadWhitelistFromDatabase()
    {
        try
        {
            if (httpClient == null || string.IsNullOrEmpty(serverAddress))
            {
                Console.WriteLine("[ERROR] Configuration manquante");
                return;
            }

            string url = $"{SUPABASE_URL}/rest/v1/{TABLE_NAME}?server_IPAdress=eq.{serverAddress}&select=match_playersteam_1,match_playersteam_2,match_playersteam_3,match_playersteam_4,match_playersteam_5,match_playersteam_6,match_playersteam_7,match_playersteam_8,match_playersteam_9,match_playersteam_10";

            httpClient.DefaultRequestHeaders.Clear();
            httpClient.DefaultRequestHeaders.Add("apikey", SUPABASE_ANON_KEY);
            httpClient.DefaultRequestHeaders.Add("Authorization", $"Bearer {SUPABASE_ANON_KEY}");

            HttpResponseMessage response = await httpClient.GetAsync(url);
            
            if (response.IsSuccessStatusCode)
            {
                string jsonResponse = await response.Content.ReadAsStringAsync();
                using JsonDocument document = JsonDocument.Parse(jsonResponse);
                var serverDataArray = document.RootElement;

                whitelistedSteamIds.Clear();

                if (serverDataArray.GetArrayLength() > 0)
                {
                    var server = serverDataArray[0];
                    
                    for (int i = 1; i <= 10; i++)
                    {
                        string columnName = $"match_playersteam_{i}";
                        if (server.TryGetProperty(columnName, out JsonElement steamIdElement))
                        {
                            string? steamId = steamIdElement.GetString()?.Trim();
                            if (!string.IsNullOrEmpty(steamId) && steamId != "null" && !whitelistedSteamIds.Contains(steamId))
                            {
                                whitelistedSteamIds.Add(steamId);
                            }
                        }
                    }

                    Console.WriteLine($"[WHITELIST] {whitelistedSteamIds.Count} joueurs autorisés");
                }
                else
                {
                    Console.WriteLine("[WHITELIST] Aucune configuration trouvée");
                }
            }
            else
            {
                Console.WriteLine($"[ERROR] Supabase: {response.StatusCode}");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[ERROR] Chargement whitelist: {ex.Message}");
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

            // Recharger la whitelist si ça fait plus de 10 secondes
            bool shouldReload = false;
            if (!isReloadingWhitelist && (DateTime.Now - lastWhitelistReload).TotalSeconds > 10)
            {
                shouldReload = true;
                isReloadingWhitelist = true;
            }

            if (shouldReload)
            {
                Task.Run(async () =>
                {
                    try
                    {
                        await LoadWhitelistFromDatabase();
                        lastWhitelistReload = DateTime.Now;
                    }
                    finally
                    {
                        isReloadingWhitelist = false;
                    }
                });
            }

            // Vérifier l'autorisation
            Server.NextFrame(() =>
            {
                try
                {
                    if (player != null && player.IsValid && player.Connected == PlayerConnectedState.PlayerConnected)
                    {
                        CheckPlayerAuthorizationSimple(player);
                    }
                }
                catch (Exception checkEx)
                {
                    Console.WriteLine($"[ERROR] {checkEx.Message}");
                }
            });
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[ERROR] OnPlayerConnect: {ex.Message}");
        }

        return HookResult.Continue;
    }
    
    private void CheckPlayerAuthorizationSimple(CCSPlayerController player)
    {
        try
        {
            if (!whitelistEnabled) return;
            
            string playerSteamId64 = player.SteamID.ToString();
            string playerName = player.PlayerName ?? "Unknown";
            
            // Si pas de whitelist, autoriser par sécurité
            if (whitelistedSteamIds.Count == 0) return;
            
            bool isAuthorized = whitelistedSteamIds.Contains(playerSteamId64);
            
            if (!isAuthorized)
            {
                lock (kickLock)
                {
                    if (recentlyKickedPlayers.Contains(playerSteamId64)) return;
                    recentlyKickedPlayers.Add(playerSteamId64);
                }
                
                Console.WriteLine($"[KICK] Joueur non autorisé:");
                Console.WriteLine($"  - Nom: \"{playerName}\"");
                Console.WriteLine($"  - SteamID: {playerSteamId64}");
                Console.WriteLine($"  - UserID: {player.UserId}");
                Console.WriteLine($"  - Slot: {player.Slot}");
                
                Task.Run(() =>
                {
                    Thread.Sleep(100);
                    Server.NextFrame(() =>
                    {
                        try
                        {
                            if (player != null && player.IsValid && player.Connected == PlayerConnectedState.PlayerConnected)
                            {
                                // Utiliser l'API directe plutôt que les commandes console
                                Server.ExecuteCommand($"kickid {player.UserId} \"Accès non autorisé\"");
                                Console.WriteLine($"[KICK] {playerName} (SteamID: {player.SteamID}) - Kick par UserID");
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"[ERROR] Kick par UserID: {ex.Message}");
                            // Fallback : utiliser le slot
                            try
                            {
                                if (player != null && player.IsValid)
                                {
                                    Server.ExecuteCommand($"kick #{player.Slot} \"Accès non autorisé\"");
                                    Console.WriteLine($"[KICK] {playerName} - Fallback par Slot #{player.Slot}");
                                }
                            }
                            catch (Exception slotEx)
                            {
                                Console.WriteLine($"[ERROR] Kick par Slot: {slotEx.Message}");
                                // Dernier recours : essayer avec le SteamID
                                try
                                {
                                    if (player != null && player.IsValid)
                                    {
                                        Server.ExecuteCommand($"banid 0 {player.SteamID} \"Accès non autorisé\"; kickid {player.UserId}");
                                        Console.WriteLine($"[KICK] {playerName} - Dernier recours SteamID");
                                    }
                                }
                                catch (Exception steamEx)
                                {
                                    Console.WriteLine($"[ERROR] Toutes méthodes échouées: {steamEx.Message}");
                                }
                            }
                        }
                    });
                });
                
                Task.Delay(10000).ContinueWith(_ =>
                {
                    lock (kickLock) { recentlyKickedPlayers.Remove(playerSteamId64); }
                });
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"[ERROR] Auth: {ex.Message}");
        }
    }


    // Commande pour recharger la whitelist manuellement
    [ConsoleCommand("css_reload_whitelist", "Recharge la whitelist depuis la base de données")]
    [CommandHelper(minArgs: 0, usage: "", whoCanExecute: CommandUsage.SERVER_ONLY)]
    public void OnReloadWhitelistCommand(CCSPlayerController? player, CommandInfo commandInfo)
    {
        _ = LoadWhitelistFromDatabase();
        commandInfo.ReplyToCommand("Rechargement en cours...");
    }

    [ConsoleCommand("css_whitelist_status", "Affiche le statut de la whitelist")]
    [CommandHelper(minArgs: 0, usage: "", whoCanExecute: CommandUsage.SERVER_ONLY)]
    public void OnWhitelistStatusCommand(CCSPlayerController? player, CommandInfo commandInfo)
    {
        Console.WriteLine($"[STATUS] Serveur: {serverAddress}");
        Console.WriteLine($"[STATUS] Joueurs autorisés: {whitelistedSteamIds.Count}");
        Console.WriteLine($"[STATUS] État: {(whitelistEnabled ? "ACTIVÉE" : "DÉSACTIVÉE")}");
        
        commandInfo.ReplyToCommand($"Whitelist: {whitelistedSteamIds.Count} joueurs autorisés");
    }

    [ConsoleCommand("css_whitelist_toggle", "Active/désactive la whitelist")]
    [CommandHelper(minArgs: 0, usage: "", whoCanExecute: CommandUsage.SERVER_ONLY)]
    public void OnWhitelistToggleCommand(CCSPlayerController? player, CommandInfo commandInfo)
    {
        whitelistEnabled = !whitelistEnabled;
        string status = whitelistEnabled ? "ACTIVÉE" : "DÉSACTIVÉE";
        Console.WriteLine($"[CONFIG] Whitelist {status}");
        commandInfo.ReplyToCommand($"Whitelist {status}");
    }

    public override void Unload(bool hotReload)
    {
        httpClient?.Dispose();
        Console.WriteLine("[PLUGIN] QuickFrag Whitelist déchargé");
    }
}