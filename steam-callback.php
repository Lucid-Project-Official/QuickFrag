<?php
// 🎯 QuickFrag.io - Callback Steam Ultra Simple
// Déployez ce fichier sur n'importe quel hébergeur PHP

header('Content-Type: text/html; charset=utf-8');

// Configuration
$SUPABASE_URL = "https://votre-projet.supabase.co";
$SUPABASE_KEY = "votre_cle_anonyme";
$DISCORD_WEBHOOK = "https://discord.com/api/webhooks/votre_webhook";

function verify_steam_openid() {
    // Préparer les paramètres de vérification
    $params = $_GET;
    $params['openid.mode'] = 'check_authentication';
    
    // Faire la requête à Steam
    $post_data = http_build_query($params);
    $context = stream_context_create([
        'http' => [
            'method' => 'POST',
            'header' => 'Content-Type: application/x-www-form-urlencoded',
            'content' => $post_data,
            'timeout' => 10
        ]
    ]);
    
    $result = file_get_contents('https://steamcommunity.com/openid/login', false, $context);
    
    if (strpos($result, 'is_valid:true') !== false) {
        // Extraire le Steam ID
        if (isset($_GET['openid_identity'])) {
            if (preg_match('/steamcommunity\.com\/openid\/id\/(\d+)/', $_GET['openid_identity'], $matches)) {
                return $matches[1];
            }
        }
    }
    
    return null;
}

function update_supabase($steam_id, $discord_id) {
    global $SUPABASE_URL, $SUPABASE_KEY;
    
    // Vérifier si Steam ID déjà utilisé
    $check_url = "$SUPABASE_URL/rest/v1/Players?Steam_PlayerID=eq.$steam_id&select=Discord_PlayerID";
    $check_headers = [
        "apikey: $SUPABASE_KEY",
        "Authorization: Bearer $SUPABASE_KEY",
        "Content-Type: application/json"
    ];
    
    $check_context = stream_context_create([
        'http' => [
            'method' => 'GET',
            'header' => implode("\r\n", $check_headers)
        ]
    ]);
    
    $check_result = file_get_contents($check_url, false, $check_context);
    $existing = json_decode($check_result, true);
    
    if (!empty($existing)) {
        return false; // Steam ID déjà utilisé
    }
    
    // Vérifier si utilisateur Discord existe
    $user_url = "$SUPABASE_URL/rest/v1/Players?Discord_PlayerID=eq.$discord_id";
    $user_context = stream_context_create([
        'http' => [
            'method' => 'GET',
            'header' => implode("\r\n", $check_headers)
        ]
    ]);
    
    $user_result = file_get_contents($user_url, false, $user_context);
    $user_data = json_decode($user_result, true);
    
    $data = json_encode([
        'Steam_PlayerID' => $steam_id,
        'Discord_PlayerID' => $discord_id,
        'PlayerName' => "User_$discord_id",
        'PlayerRank' => 'SilverOne',
        'PlayerElo' => 1000
    ]);
    
    if (!empty($user_data)) {
        // Mettre à jour
        $update_url = "$SUPABASE_URL/rest/v1/Players?Discord_PlayerID=eq.$discord_id";
        $update_context = stream_context_create([
            'http' => [
                'method' => 'PATCH',
                'header' => implode("\r\n", array_merge($check_headers, ["Prefer: return=minimal"])),
                'content' => $data
            ]
        ]);
        file_get_contents($update_url, false, $update_context);
    } else {
        // Créer nouveau
        $insert_url = "$SUPABASE_URL/rest/v1/Players";
        $insert_context = stream_context_create([
            'http' => [
                'method' => 'POST',
                'header' => implode("\r\n", array_merge($check_headers, ["Prefer: return=minimal"])),
                'content' => $data
            ]
        ]);
        file_get_contents($insert_url, false, $insert_context);
    }
    
    return true;
}

function send_discord_notification($discord_id, $steam_id) {
    global $DISCORD_WEBHOOK;
    
    $embed = [
        'title' => '✅ Compte Steam lié avec succès !',
        'description' => "Votre compte Steam a été lié à votre compte Discord.\n\n**Steam ID**: $steam_id\n**Rang initial**: Silver I\n**ELO initial**: 1000",
        'color' => 3066993
    ];
    
    $webhook_data = json_encode([
        'content' => "<@$discord_id>",
        'embeds' => [$embed]
    ]);
    
    $context = stream_context_create([
        'http' => [
            'method' => 'POST',
            'header' => 'Content-Type: application/json',
            'content' => $webhook_data
        ]
    ]);
    
    file_get_contents($DISCORD_WEBHOOK, false, $context);
}

// Traitement principal
$discord_id = $_GET['discord_id'] ?? null;
$token = $_GET['token'] ?? null;

if (!$discord_id || !$token) {
    die('❌ Paramètres manquants');
}

// Vérifier Steam OpenID
$steam_id = verify_steam_openid();

if (!$steam_id) {
    die('❌ Vérification Steam échouée');
}

// Mettre à jour la base de données
if (!update_supabase($steam_id, $discord_id)) {
    die('❌ Ce compte Steam est déjà lié à un autre utilisateur');
}

// Envoyer notification Discord
send_discord_notification($discord_id, $steam_id);

?>
<!DOCTYPE html>
<html>
<head>
    <title>QuickFrag - Liaison réussie</title>
    <meta charset="utf-8">
    <style>
        body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #f0f0f0; }
        .success { background: white; padding: 30px; border-radius: 10px; display: inline-block; box-shadow: 0 5px 15px rgba(0,0,0,0.1); }
        h1 { color: #27ae60; }
    </style>
</head>
<body>
    <div class="success">
        <h1>✅ Compte lié avec succès !</h1>
        <p>Votre compte Steam a été lié à votre compte Discord.</p>
        <p><strong>Steam ID:</strong> <?= htmlspecialchars($steam_id) ?></p>
        <p>Vous devriez recevoir une confirmation sur Discord.</p>
        <p>Vous pouvez maintenant fermer cette page.</p>
    </div>
</body>
</html> 