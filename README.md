# FFMPEG Media Annihilator 
<img src="https://img.shields.io/badge/Python-3.6+-blue?style=for-the-badge&logo=python&logoColor=white">
<img src="https://img.shields.io/badge/FFMPEG-Required-orange?style=for-the-badge&logo=ffmpeg&logoColor=white">
<img src="https://img.shields.io/badge/PyQt6-GUI-red?style=for-the-badge&logo=pyqt&logoColor=white">
<img src="assets/icon256.png" width="256" height="256">


A powerful GUI application to manipulate and annihilate media files with extreme effects using FFMPEG. Now supports both video and audio processing with enhanced multi-stage pipeline for maximum audio intensity!


## Demos

For comprehensive demo showcases and side-by-side comparisons, see **[DEMOS.md](./DEMOS.md)**

### Quick Preview
- **Video Processing**: See original vs annihilated videos
- **Audio Processing**: Hear original vs processed audio
- **Side-by-Side**: Direct comparison of effects
- **Educational**: Demonstrates software capabilities

**Note**: All demos are for educational purposes only. Original content rights belong to respective owners.

## Features

### Media Support
- **Video Processing**: Full video effects with audio processing
- **Audio-Only Processing**: Dedicated audio file support (MP3, WAV, FLAC, OGG, AAC)
- **Smart UI**: Automatically hides video controls for audio files
- **Enhanced Audio Mode**: Multi-stage pipeline for maximum effect intensity

### Video Effects
- **Resolution Scaling**: Reduce video resolution to 10%-100% of original
- **Blur**: Apply Gaussian blur (0-10 sigma)
- **Compression**: Adjust CRF (18-51) for compression artifacts
- **Media Artifacts**: Add noise, color shifts, and scanlines for authentic media degradation
- **Frame Rate Control**: Adjust playback speed (0.1-120 fps)
- **Hue Shift**: Shifts the color hue of the video
- **Saturation**: Adjusts the color saturation of the video

### Audio Effects
- **Volume Control**: 0% to 500% boost (earrape capable!)
- **Pitch Control**: Adjust pitch in semitones (-12 to +12, one octave range)
- **Speed Control**: Change playback speed (0.5x to 2.0x)
- **Compression**: Reduce audio bitrate (16k-64k)
- **High Pass Filter**: Remove low frequencies (0-1000Hz)
- **Low Pass Filter**: Remove high frequencies (1000-8000Hz)
- **Reverb**: Add echo/delay effects
- **Distortion**: Bit-crushing for gritty texture
- **Sample Rate**: Quality reduction (8kHz-48kHz)
- **Enhanced Processing**: Multi-stage pipeline eliminates A/V sync constraints
- **Metadata Annihilation**: Eradicates all metadata from the file depending of the chosen mode;
  - **Nuked**: Removes all metadata
  - **Corrupted**: Removes all metadata and sets all tags to weird values
  - **Randomized**: Removes all metadata and sets all tags to random values


### GUI Features
- Modern PyQt6 interface with dark theme
- File selection for input/output
- Real-time parameter adjustment
- Live preview with debounced updates
- Progress tracking during processing
- Dynamic earrape warnings (200%+ volume)
- Automatic fallback for complex audio effects
- FFMPEG command preview
- Cross-platform compatibility
- Adaptive UI based on media type


## Requirements

- Python 3.6+
- PyQt6
- FFMPEG (must be in system PATH)

## Installation

1. Ensure FFMPEG is installed and in your system PATH
2. Clone or download this repository
3. Run the GUI application:

```bash
python FFMPEG-ANNIHILATOR.py
```

## Usage

1. **Select Media**: Click "Select Input Video/Audio" to choose your source file
   - Video files: MP4, AVI, MOV, MKV, WebM, FLV
   - Audio files: MP3, WAV, FLAC, OGG, AAC

2. **Adjust Effects**: Use sliders and controls to customize effects
   - Video effects automatically hide for audio files
   - All audio effects available for both media types

3. **Enhanced Mode** (Video files only):
   - Enable "Enhanced Audio Processing" for maximum effect intensity
   - Uses multi-stage pipeline for consistent audio effects

4. **Preview**: Click "Update Preview" to see the FFMPEG command

5. **Process**: Click "Process Media" to apply the effects
   - Enhanced mode shows 4-step progress for video files
   - Single-step processing for audio files

6. **Wait**: Processing completes automatically with success notification



## Supported Formats

### Video Files
- **Input**: MP4, AVI, MOV, MKV, WebM, FLV, WMV
- **Output**: MP4, AVI, MOV (default: MP4)

### Audio Files
- **Input**: MP3, WAV, FLAC, OGG, AAC, M4A
- **Output**: MP3, WAV, AAC (default: MP3)

## Tips

### Video Processing
- Start with lower resolution (25%) and high compression (35+) for strong VHS effect
- Enable VHS artifacts for authentic vintage look
- Use frame rate reduction for choppy, old-school feel

### Audio Processing
- Combine audio filters (300Hz high pass + 3000Hz low pass) for phone-like quality
- Use enhanced mode for video files to get same intensity as audio-only processing
- Volume 200%+ triggers earrape warnings for safety
- Lower sample rates (8kHz) create vintage telephone quality
- **Pitch Effects**: Use ±12 semitones for one octave up/down, smaller changes for subtle tuning
- **Speed Effects**: 0.5x-0.8x for dramatic slow-motion, 1.2x-2.0x for fast-paced effects
- **Combined Effects**: Pitch + speed together can create chipmunk or deep voice effects

### Enhanced Audio Mode
- Enable "Enhanced Audio Processing" for maximum effect intensity in video files
- Eliminates A/V sync constraints for stronger audio effects
- Uses 4-stage pipeline: Extract audio -> Process audio -> Process video -> Merge
- Results in consistent audio effects across all media types

### General
- Use "Update Preview" to understand the FFMPEG command being generated
- UI automatically adapts based on media type (video vs audio)
- Enhanced mode only available for video files with audio processing enabled

## Troubleshooting

- **FFMPEG not found**: Ensure FFMPEG is installed and in your system PATH
- **Processing fails**: Check that input file exists and output location is writable
- **No audio effects**: Make sure "Enable Audio Processing" is checked
- **Enhanced mode not working**: Only available for video files with audio processing enabled
- **Audio effects weaker in video files**: Enable "Enhanced Audio Processing" for maximum intensity
- **Taskbar icon missing**: Ensure Windows AppUserModelID is set (automatically handled)
- **QPixmap errors**: Normal for audio files - preview images are not generated for audio-only content

## License
This project is licensed under the MIT License - see the [LICENSE](./LICENSE) file for details.
