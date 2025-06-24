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
            if (httpClient == null)
            {
                Console.WriteLine("HttpClient non initialisé");
                return;
            }

            if (string.IsNullOrEmpty(serverAddress))
            {
                Console.WriteLine("Adresse du serveur non disponible pour la recherche en base de données");
                return;
            }

            // Construire l'URL de l'API Supabase pour récupérer les données du serveur
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
                    
                    // Extraire tous les SteamIDs des colonnes match_playersteam_1 à match_playersteam_10
                    for (int i = 1; i <= 10; i++)
                    {
                        string columnName = $"match_playersteam_{i}";
                        if (server.TryGetProperty(columnName, out JsonElement steamIdElement))
                        {
                            string? steamId = steamIdElement.GetString()?.Trim();
                            if (!string.IsNullOrEmpty(steamId) && steamId != "null")
                            {
                                whitelistedSteamIds.Add(steamId);
                            }
                        }
                    }

                    Console.WriteLine($"Whitelist chargée : {whitelistedSteamIds.Count} joueurs autorisés");
                    Server.PrintToConsole($"Whitelist mise à jour : {whitelistedSteamIds.Count} joueurs autorisés pour ce serveur");
                }
                else
                {
                    Console.WriteLine($"Aucune configuration trouvée pour le serveur {serverAddress}");
                }
            }
            else
            {
                Console.WriteLine($"Erreur lors de la récupération des données : {response.StatusCode}");
            }
        }
        catch (Exception ex)
        {
            Console.WriteLine($"Erreur lors du chargement de la whitelist : {ex.Message}");
        }
    }

    [GameEventHandler]
    public HookResult OnPlayerConnectFull(EventPlayerConnectFull @event, GameEventInfo info)
    {
        var player = @event.Userid;
        if (player == null || !player.IsValid)
            return HookResult.Continue;

        // Vérifier si le joueur est dans la whitelist
        string playerSteamId = player.SteamID.ToString();
        
        if (!whitelistedSteamIds.Contains(playerSteamId))
        {
            // Le joueur n'est pas autorisé, le kicker
            Server.NextFrame(() =>
            {
                if (player.IsValid && player.Connected == PlayerConnectedState.PlayerConnected)
                {
                    Server.ExecuteCommand($"kickid {player.UserId} \"Vous ne pouvez pas rejoindre ce match.\"");
                    Console.WriteLine($"Joueur {player.PlayerName} (SteamID: {playerSteamId}) exclu - non autorisé");
                }
            });
        }
        else
        {
            Console.WriteLine($"Joueur {player.PlayerName} (SteamID: {playerSteamId}) autorisé à rejoindre");
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