# 桌面大肥鱼 · Windows 系统媒体（SMTC）适配器
# 输出：{ title, artist, album, duration, elapsed, playing, app }
# 覆盖 Windows 上的网易云音乐、QQ 音乐、Apple Music、Spotify 等。
$ErrorActionPreference = 'Stop'
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
try {
  Add-Type -AssemblyName System.Runtime.WindowsRuntime | Out-Null
  $asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | Where-Object {
    $_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and
    $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'
  })[0]
  function Await($WinRtTask, $ResultType) {
    $asTask = $asTaskGeneric.MakeGenericMethod($ResultType)
    $netTask = $asTask.Invoke($null, @($WinRtTask))
    $netTask.Wait(-1) | Out-Null
    $netTask.Result
  }
  [Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager, Windows.Media.Control, ContentType = WindowsRuntime] | Out-Null
  $mgr = Await ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager]::RequestAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionManager])
  $session = $mgr.GetCurrentSession()
  if (-not $session) {
    [pscustomobject]@{ playing = $false } | ConvertTo-Json -Compress
    exit 0
  }
  $props = Await ($session.TryGetMediaPropertiesAsync()) ([Windows.Media.Control.GlobalSystemMediaTransportControlsSessionMediaProperties])
  $timeline = $session.GetTimelineProperties()
  $info = $session.GetPlaybackInfo()
  $status = if ($info) { $info.PlaybackStatus.ToString() } else { 'Closed' }
  [pscustomobject]@{
    title = $props.Title
    artist = $props.Artist
    album = $props.AlbumTitle
    duration = [math]::Round($timeline.EndTime.TotalSeconds, 2)
    elapsed = [math]::Round($timeline.Position.TotalSeconds, 2)
    playing = ($status -eq 'Playing')
    app = $session.SourceAppUserModelId
  } | ConvertTo-Json -Compress
} catch {
  [pscustomobject]@{ playing = $false; error = "$_" } | ConvertTo-Json -Compress
  exit 0
}
