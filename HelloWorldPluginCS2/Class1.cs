using CounterStrikeSharp.API;
using CounterStrikeSharp.API.Core;

namespace HelloWorldPluginCS2;

public class MonPlugin : BasePlugin
{
    public override string ModuleName => "yoloooooo";
    public override string ModuleVersion => "1.0.0";
    public override string ModuleAuthor => "Linox";
    public override string ModuleDescription => "Un plugin test pour CS2";

    public override void Load(bool hotReload)
    {
        Console.WriteLine("Plugin CS2 chargé !");
        Server.PrintToConsole("MonPluginCS2 est actif !");
    }
}