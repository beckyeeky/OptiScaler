$ErrorActionPreference = 'Stop'
$root = (Resolve-Path (Join-Path $PSScriptRoot '../..')).Path
$vswhere = Join-Path ${env:ProgramFiles(x86)} 'Microsoft Visual Studio/Installer/vswhere.exe'
$vs = & $vswhere -latest -version '[17.0,18.0)' -products '*' -requires Microsoft.VisualStudio.Component.VC.Tools.x86.x64 -property installationPath
if (-not $vs) { throw 'VS2022 C++ x64 tools are required; nothing will be installed automatically.' }
$out = Join-Path $root 'x64/font-smoke'
New-Item -ItemType Directory -Path $out -Force | Out-Null
$data = Get-Content (Join-Path $root 'tools/l10n/zh-CN.json') -Raw -Encoding utf8 | ConvertFrom-Json
$chars = ($data.translations.target -join '').ToCharArray() | ForEach-Object { [int]$_ } | Where-Object { $_ -gt 127 } | Sort-Object -Unique
$chars | Out-File (Join-Path $out 'required-chars.txt') -Encoding ascii
$dev = Join-Path $vs 'Common7/Tools/VsDevCmd.bat'
# Build only an isolated ImGui/font console program. No injection, game, or renderer is loaded.
$command = 'call "{0}" -arch=x64 -host_arch=x64 && cl /nologo /std:c++17 /EHsc /MD /utf-8 /DNDEBUG /I"{1}/OptiScaler/include" /I"{1}/external/freetype" "{1}/tools/l10n/font_smoke.cpp" "{1}/OptiScaler/include/imgui/imgui.cpp" "{1}/OptiScaler/include/imgui/imgui_draw.cpp" "{1}/OptiScaler/include/imgui/imgui_tables.cpp" "{1}/OptiScaler/include/imgui/imgui_widgets.cpp" "{1}/OptiScaler/include/imgui/misc/freetype/imgui_freetype.cpp" "{1}/external/freetype/freetype.lib" /Fe:font-smoke.exe /link user32.lib' -f $dev,$root
Push-Location $out
try {
    & cmd.exe /d /c $command
    if ($LASTEXITCODE -ne 0) { throw "Font test compile failed: $LASTEXITCODE" }
    & ./font-smoke.exe
    if ($LASTEXITCODE -ne 0) { throw "Font test failed: $LASTEXITCODE" }
} finally { Pop-Location }
