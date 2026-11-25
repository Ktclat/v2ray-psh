using ServiceLib.Common;

if (args.Length != 1)
    throw new ArgumentException("Expected output directory.");

const string http = "http://127.0.0.1:18081";
const string socks = "socks5://127.0.0.1:18081";
Directory.CreateDirectory(args[0]);

string Expected(params string[] lines) => string.Join(Environment.NewLine, lines) + Environment.NewLine;
void RequireEqual(string actual, string expected)
{
    if (actual != expected)
        throw new InvalidOperationException($"Unexpected terminal command. Expected: {expected}; got: {actual}");
}

string Legacy(string verb) => Expected(
    $"{verb} http_proxy={http}", $"{verb} https_proxy={http}", $"{verb} all_proxy={socks}", "",
    $"{verb} HTTP_PROXY={http}", $"{verb} HTTPS_PROXY={http}", $"{verb} ALL_PROXY={socks}");

var cmd = TerminalProxyCommands.Create(TerminalProxyShell.Cmd, http, socks);
RequireEqual(cmd, Legacy("set"));
RequireEqual(TerminalProxyCommands.Create(TerminalProxyShell.Posix, http, socks), Legacy("export"));
var powershell = TerminalProxyCommands.Create(TerminalProxyShell.PowerShell, http, socks);
RequireEqual(powershell, Expected(
    $"$env:HTTP_PROXY = '{http}'", $"$env:HTTPS_PROXY = '{http}'", $"$env:ALL_PROXY = '{socks}'"));
RequireEqual(TerminalProxyCommands.Create(TerminalProxyShell.PowerShell, "a'b", socks).Split(Environment.NewLine)[0],
    "$env:HTTP_PROXY = 'a''b'");

File.WriteAllText(Path.Combine(args[0], "verify-cmd.cmd"), "@echo off" + Environment.NewLine + cmd + Expected(
    $"if not \"%HTTP_PROXY%\"==\"{http}\" exit /b 1",
    $"if not \"%HTTPS_PROXY%\"==\"{http}\" exit /b 1",
    $"if not \"%ALL_PROXY%\"==\"{socks}\" exit /b 1",
    "exit /b 0"));
File.WriteAllText(Path.Combine(args[0], "proxy-env.ps1"), powershell);
Console.WriteLine("CMD, POSIX, PowerShell and PowerShell quoting contracts passed.");
