param(
  [string]$ScriptPath = "docs/demo/demo-script.json",
  [string]$WorkDir = "_demo_work",
  [string]$VoiceName = "Microsoft Huihui Desktop"
)

$ErrorActionPreference = "Stop"
$audioDir = Join-Path $WorkDir "audio"
New-Item -ItemType Directory -Force -Path $audioDir | Out-Null

Add-Type -AssemblyName System.Speech
$segments = Get-Content -Raw -Encoding UTF8 -LiteralPath $ScriptPath | ConvertFrom-Json
$synth = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice = $synth.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Name -eq $VoiceName } | Select-Object -First 1
if ($voice) {
  $synth.SelectVoice($VoiceName)
}
$synth.Rate = 0
$synth.Volume = 100

for ($i = 0; $i -lt $segments.Count; $i++) {
  $fileName = "segment_{0:D2}.wav" -f ($i + 1)
  $filePath = Join-Path $audioDir $fileName
  $synth.SetOutputToWaveFile((Resolve-Path -LiteralPath $audioDir).Path + [System.IO.Path]::DirectorySeparatorChar + $fileName)
  $synth.Speak([string]$segments[$i].text)
}

$synth.SetOutputToNull()
$synth.Dispose()

python scripts/demo/combine_demo_audio.py `
  --script $ScriptPath `
  --audio-dir $audioDir `
  --out-audio (Join-Path $WorkDir "demo-narration.wav") `
  --out-srt "docs/demo/demo-subtitles.srt" `
  --out-timeline (Join-Path $WorkDir "timeline.json")
