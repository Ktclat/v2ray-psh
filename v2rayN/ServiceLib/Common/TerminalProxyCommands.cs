using System.Text;

namespace ServiceLib.Common;

internal enum TerminalProxyShell
{
    Cmd,
    Posix,
    PowerShell
}

internal static class TerminalProxyCommands
{
    internal static string Create(TerminalProxyShell shell, string httpProxy, string socksProxy)
    {
        if (shell == TerminalProxyShell.PowerShell)
        {
            return new StringBuilder()
                .AppendLine($"$env:HTTP_PROXY = {PowerShellLiteral(httpProxy)}")
                .AppendLine($"$env:HTTPS_PROXY = {PowerShellLiteral(httpProxy)}")
                .AppendLine($"$env:ALL_PROXY = {PowerShellLiteral(socksProxy)}")
                .ToString();
        }

        // Keep the existing CMD and POSIX output, including case and line order.
        var verb = shell == TerminalProxyShell.Cmd ? "set" : "export";
        return new StringBuilder()
            .AppendLine($"{verb} http_proxy={httpProxy}")
            .AppendLine($"{verb} https_proxy={httpProxy}")
            .AppendLine($"{verb} all_proxy={socksProxy}")
            .AppendLine()
            .AppendLine($"{verb} HTTP_PROXY={httpProxy}")
            .AppendLine($"{verb} HTTPS_PROXY={httpProxy}")
            .AppendLine($"{verb} ALL_PROXY={socksProxy}")
            .ToString();
    }

    private static string PowerShellLiteral(string value) => $"'{value.Replace("'", "''")}'";
}
