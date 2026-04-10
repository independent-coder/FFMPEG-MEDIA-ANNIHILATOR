param(
    [Parameter(Mandatory=$true)]
    [string]$Original,

    [Parameter(Mandatory=$true)]
    [string]$Processed,

    [double]$Window = 15.0,
    [double]$Threshold = 0.4,
    [switch]$AutoSegment,
    [double]$ManualStart = 0,
    [double]$ManualEnd = 15
)

# === Validate files ===
if (-not (Test-Path -LiteralPath $Original)) {
    Write-Host "Original file not found: $Original"
    exit 1
}

if (-not (Test-Path -LiteralPath $Processed)) {
    Write-Host "Processed file not found: $Processed"
    exit 1
}

# === Generate output filename ===
$originalName = [System.IO.Path]::GetFileNameWithoutExtension($Original)
$processedName = [System.IO.Path]::GetFileNameWithoutExtension($Processed)
$Output = "${originalName}_vs_${processedName}.mp4"

Write-Host "=== Video Comparison Tool ==="
Write-Host "Original: $Original"
Write-Host "Processed: $Processed"
Write-Host "Output: $Output"
Write-Host ""

if ($AutoSegment) {
    Write-Host "=== Finding Best Segment ==="
    Write-Host "Analyzing scene changes in $Original..."
    Write-Host ""

    # === Run FFmpeg and capture output for original video ===
    $ffmpegOutput = & ffmpeg -hide_banner -i "$Original" -filter:v "select='gt(scene,$Threshold)',metadata=print" -f null - 2>&1

    # === Extract timestamps ===
    $timestamps = @()

    foreach ($line in $ffmpegOutput) {
        if ($line -match "pts_time:([0-9\.]+)") {
            $timestamps += [double]$matches[1]
        }
    }

    if ($timestamps.Count -eq 0) {
        Write-Host "No scene changes detected in original video."
        Write-Host "Using default 0-15 second segment."
        $ManualStart = 0
        $ManualEnd = 15
    } else {
        Write-Host "Found $($timestamps.Count) scene changes"
        Write-Host ""

        # === Find densest window ===
        $bestStart = 0
        $maxCount = 0

        for ($i = 0; $i -lt $timestamps.Count; $i++) {
            $start = $timestamps[$i]
            $end = $start + $Window

            $count = 0
            foreach ($t in $timestamps) {
                if ($t -ge $start -and $t -le $end) {
                    $count++
                }
            }

            if ($count -gt $maxCount) {
                $maxCount = $count
                $bestStart = $start
            }
        }

        $ManualStart = [math]::Round($bestStart, 2)
        $ManualEnd = [math]::Round($bestStart + $Window, 2)

        Write-Host "Best segment found!"
        Write-Host "Start: $ManualStart s"
        Write-Host "End:   $ManualEnd s"
        Write-Host "Scene changes in window: $maxCount"
        Write-Host ""
    }
} else {
    Write-Host "Using manual segment: $ManualStart - $ManualEnd seconds"
}

Write-Host "=== Creating Side-by-Side Comparison ==="
Write-Host "Duration: $($ManualEnd - $ManualStart) seconds"
Write-Host ""

# === Calculate duration ===
$duration = $ManualEnd - $ManualStart
$audioSwitchTime = $duration / 2

# === Build FFmpeg command ===
$originalAbs = (Resolve-Path -LiteralPath $Original).Path
$processedAbs = (Resolve-Path -LiteralPath $Processed).Path
$outputAbs = Join-Path (Get-Location) $Output

$ffmpegArgs = @(
    "-y"
    "-i", $originalAbs
    "-i", $processedAbs
    "-filter_complex", "[0:v]trim=$ManualStart`:$ManualEnd,setpts=PTS-STARTPTS,scale=-1:360[leftbase];[1:v]trim=$ManualStart`:$ManualEnd,setpts=PTS-STARTPTS,scale=-1:360[rightbase];[leftbase]drawtext=text='Original':x=10:y=10:fontsize=24:fontcolor=white:fontfile='C\:/Windows/Fonts/arial.ttf'[left];[rightbase]drawtext=text='Annihilated':x=10:y=10:fontsize=24:fontcolor=white:fontfile='C\:/Windows/Fonts/arial.ttf'[right];[left][right]hstack=inputs=2[vid];[vid]drawtext=text='Audio\: ORIGINAL':x=(w-text_w)/2:y=h-40:fontsize=28:fontcolor=white:enable='lt(t,$audioSwitchTime)'[v1];[v1]drawtext=text='Audio\: ANNIHILATED':x=(w-text_w)/2:y=h-40:fontsize=28:fontcolor=white:enable='gte(t,$audioSwitchTime)'[v];[0:a]atrim=$ManualStart`:$($ManualStart + $audioSwitchTime),asetpts=PTS-STARTPTS[a1];[1:a]atrim=$($ManualStart + $audioSwitchTime)`:$ManualEnd,asetpts=PTS-STARTPTS[a2];[a1][a2]concat=n=2:v=0:a=1[a]"
    "-map", "[v]"
    "-map", "[a]"
    "-c:v", "libx264"
    "-crf", "18"
    "-preset", "fast"
    "-c:a", "aac"
    "-b:a", "128k"
    $outputAbs
)

# === Execute FFmpeg ===
try {
    & ffmpeg @ffmpegArgs
    Write-Host ""
    Write-Host "Done! Output: $Output"
    Write-Host ""
} catch {
    Write-Host "Error running FFmpeg: $_"
    exit 1
}

Write-Host "=== Usage Examples ==="
Write-Host ""
Write-Host "Auto-find best segment:"
Write-Host ".\compare_videos_merged.ps1 -Original original.mp4 -Processed processed.mp4 -AutoSegment"
Write-Host ""
Write-Host "Manual segment (0-15 seconds):"
Write-Host ".\compare_videos_merged.ps1 -Original original.mp4 -Processed processed.mp4 -ManualStart 0 -ManualEnd 15"
Write-Host ""
Write-Host "Custom window size and threshold:"
Write-Host ".\compare_videos_merged.ps1 -Original original.mp4 -Processed processed.mp4 -AutoSegment -Window 20 -Threshold 0.3"
