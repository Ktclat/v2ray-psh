param([Parameter(Mandatory = $true)][string]$CommandFile)
$ErrorActionPreference = 'Stop'
. $CommandFile
if ($env:HTTP_PROXY -cne 'http://127.0.0.1:18081' -or
    $env:HTTPS_PROXY -cne 'http://127.0.0.1:18081' -or
    $env:ALL_PROXY -cne 'socks5://127.0.0.1:18081') {
    throw 'Generated PowerShell failed to set the expected proxy environment.'
}
"Generated command verified in PowerShell $($PSVersionTable.PSVersion)"
