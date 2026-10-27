# 桌面大肥鱼 Coach · Windows 安装（终端轻量版）
# 双击/在 PowerShell 中运行： powershell -ExecutionPolicy Bypass -File scripts\install.ps1
$ErrorActionPreference = 'Stop'
$Root = Split-Path $PSScriptRoot -Parent
$Prefix = Join-Path $env:LOCALAPPDATA 'DafeiyuCoach'
$Data = if ($env:DAFEIYU_HOME) { $env:DAFEIYU_HOME } else { Join-Path $env:USERPROFILE '.dafeiyu' }
New-Item -ItemType Directory -Force -Path $Prefix, $Data, (Join-Path $Data 'music') | Out-Null
Copy-Item (Join-Path $Root 'bin\dafeiyu') $Prefix -Force
Copy-Item (Join-Path $Root 'bin\dafeiyu_music.py') $Prefix -Force
Copy-Item (Join-Path $Root 'bin\dafeiyu_tui.py') $Prefix -Force
Copy-Item (Join-Path $Root 'bin\dafeiyu_mcp.py') $Prefix -Force
Copy-Item (Join-Path $Root 'Runtime\music\*') (Join-Path $Data 'music') -Recurse -Force
$cmd = @"
@echo off
chcp 65001 >/dev/null
python "%~dp0dafeiyu" %*
"@
Set-Content -Path (Join-Path $Prefix 'dafeiyu.cmd') -Value $cmd -Encoding ASCII
foreach ($agent in @('.qoder\skills', '.claude\skills', '.codex\skills', '.dsh\skills')) {
  $dir = Join-Path $env:USERPROFILE (Join-Path $agent 'dafeiyu-coach')
  New-Item -ItemType Directory -Force -Path $dir | Out-Null
  Copy-Item (Join-Path $Root 'skills\dafeiyu-coach\SKILL.md') (Join-Path $dir 'SKILL.md') -Force
}
$qcmd = Join-Path $env:USERPROFILE '.qoder\commands'; New-Item -ItemType Directory -Force -Path $qcmd | Out-Null
Copy-Item (Join-Path $Root 'adapters\commands\dafeiyu.md') (Join-Path $qcmd 'dafeiyu.md') -Force
Write-Host ""
Write-Host "安装完成：$Prefix"
Write-Host "  终端宠物：& '$Prefix\dafeiyu.cmd' tui"
Write-Host "  或把 $Prefix 加进 PATH 后运行： dafeiyu tui"
Write-Host "  音乐：dafeiyu music on（Windows 使用系统 SMTC，需 PowerShell 5.1+）"
Write-Host "  依赖：Python 3.9+；歌词联网走 LRCLIB，可用本地 .lrc 离线。"
