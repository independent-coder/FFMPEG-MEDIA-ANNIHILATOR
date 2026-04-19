#!/usr/bin/env python3
"""
FFMPEG Media Annihilator - PyQt6 Edition
A modern GUI to manipulate video files with media effects and processing.
"""

import sys
import os
import subprocess
import threading
import re
import json
import tempfile
import shutil
import random
from pathlib import Path
from PIL import Image, ImageQt

# Set Windows AppUserModelID for proper taskbar icon
if sys.platform == 'win32':
    import ctypes
    from ctypes import wintypes
    
    # Set AppUserModelID before QApplication creation
    app_id = "FFMPEGMediaAnnihilator.App"
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(app_id)

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QGridLayout, QLabel, QPushButton, QSlider, QComboBox, QCheckBox,
    QProgressBar, QTextEdit, QGroupBox, QFileDialog, QMessageBox,
    QSplitter, QFrame, QScrollArea, QSpinBox, QDoubleSpinBox, QDialog
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize
from PyQt6.QtGui import QPixmap, QFont, QIcon, QPalette, QColor


class FFmpegWorker(QThread):
    """Worker thread for FFMPEG processing"""
    progress_updated = pyqtSignal(str)
    finished = pyqtSignal(bool, str)
    
    def __init__(self, cmd):
        super().__init__()
        self.cmd = cmd
        
    def run(self):
        try:
            print("Starting FFMPEG with command:", " ".join(self.cmd))
            
            process = subprocess.Popen(
                self.cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # Combine stderr with stdout for progress
                text=True,
                universal_newlines=True,
                bufsize=1
            )
            
            duration = None
            while True:
                output = process.stdout.readline()
                if output == '' and process.poll() is not None:
                    break
                if output:
                    output = output.strip()
                    
                    # Parse duration from FFMPEG output
                    if "Duration:" in output and duration is None:
                        import re
                        duration_match = re.search(r'Duration: (\d{2}):(\d{2}):(\d{2}\.\d{2})', output)
                        if duration_match:
                            hours, minutes, seconds = map(float, duration_match.groups())
                            duration = hours * 3600 + minutes * 60 + seconds
                            print(f"Video duration: {duration} seconds")
                    
                    # Parse progress
                    if "time=" in output and duration:
                        import re
                        time_match = re.search(r'time=(\d{2}):(\d{2}):(\d{2}\.\d{2})', output)
                        if time_match:
                            hours, minutes, seconds = map(float, time_match.groups())
                            current_time = hours * 3600 + minutes * 60 + seconds
                            progress = int((current_time / duration) * 100)
                            self.progress_updated.emit(f"Processing: {progress}%")
                            print(f"Progress: {progress}%")
                    else:
                        # Show other FFMPEG output
                        self.progress_updated.emit(output)
            
            # Wait for process to complete
            returncode = process.wait()
            print(f"FFMPEG finished with return code: {returncode}")
            
            success = returncode == 0
            if not success:
                # Convert large unsigned return codes to signed for better readability
                if returncode > 2**31:
                    signed_code = returncode - 2**32
                    error_msg = f"Exit code: {returncode} (signed: {signed_code})"
                else:
                    error_msg = f"Exit code: {returncode}"
            else:
                error_msg = ""
                
            self.finished.emit(success, error_msg)
            
        except Exception as e:
            print(f"Exception in FFmpegWorker: {e}")
            self.finished.emit(False, f"Exception: {str(e)}")


class ModernButton(QPushButton):
    """Custom styled button that adapts to theme"""
    def __init__(self, text, color_type="default"):
        super().__init__(text)
        self.color_type = color_type
        self.update_style()
    
    def update_style(self):
        """Update button style based on current theme"""
        # Get theme colors from parent if available
        theme_colors = self.get_theme_colors()
        
        color_map = {
            "default": theme_colors["button"],
            "primary": "#4CAF50",
            "secondary": "#607D8B", 
            "settings": "#9E9E9E",
            "warning": "#FF9800",
            "danger": "#F44336"
        }
        
        base_color = color_map.get(self.color_type, theme_colors["button"])
        
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {base_color};
                color: white;
                border: none;
                padding: 10px 20px;
                border-radius: 6px;
                font-weight: bold;
                font-size: 14px;
            }}
            QPushButton:hover {{
                background-color: {base_color}dd;
            }}
            QPushButton:pressed {{
                background-color: {base_color}bb;
            }}
            QPushButton:disabled {{
                background-color: {theme_colors["button"]};
                color: {theme_colors["text"]};
                opacity: 0.5;
            }}
        """)
    
    def get_theme_colors(self):
        """Get current theme colors from parent window"""
        # Try to get theme colors from parent window
        parent = self.parent()
        while parent:
            if hasattr(parent, 'current_theme'):
                themes = {
                    "Dark Theme": {
                        "button": "#4a4a4a",
                        "text": "#ffffff"
                    },
                    "Light Theme": {
                        "button": "#2196F3",
                        "text": "#ffffff"
                    },
                    "Blue Theme": {
                        "button": "#5c6bc0",
                        "text": "#ffffff"
                    },
                    "Green Theme": {
                        "button": "#66bb6a",
                        "text": "#ffffff"
                    }
                }
                return themes.get(parent.current_theme, themes["Dark Theme"])
            parent = parent.parent()
        
        # Default fallback
        return {
            "button": "#4a4a4a",
            "text": "#ffffff"
        }


class ModernGroupBox(QGroupBox):
    """Modern styled group box"""
    def __init__(self, title):
        super().__init__(title)
        self.setStyleSheet("""
            QGroupBox {
                font-weight: bold;
                font-size: 14px;
                border: 2px solid #ddd;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)


class VideoPreviewWidget(QWidget):
    """Widget for displaying video preview with multiple frames"""
    def __init__(self):
        super().__init__()
        self.preview_frames = []
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Create grid layout for multiple preview frames
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(5)
        
        # Create 4 preview frames (2x2 grid)
        for i in range(4):
            frame_label = QLabel()
            frame_label.setFixedSize(190, 107)  # Smaller size for grid
            frame_label.setStyleSheet("""
                QLabel {
                    background-color: #1e1e1e;
                    border: 2px solid #444;
                    border-radius: 6px;
                    color: #888;
                    font-size: 10px;
                }
            """)
            frame_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            frame_label.setText(f"Frame {i+1}\nNo Preview")
            
            self.preview_frames.append(frame_label)
            row = i // 2
            col = i % 2
            self.grid_layout.addWidget(frame_label, row, col)
        
        layout.addLayout(self.grid_layout)
        self.setLayout(layout)


class VideoInfoWidget(QWidget):
    """Widget for displaying video information"""
    def __init__(self, title):
        super().__init__()
        self.title = title
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Title
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Arial", 12, QFont.Weight.Bold))
        layout.addWidget(title_label)
        
        # Info grid
        info_layout = QGridLayout()
        
        # Resolution
        info_layout.addWidget(QLabel("Resolution:"), 0, 0)
        self.resolution_label = QLabel("No file selected")
        self.resolution_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.resolution_label, 0, 1)
        
        # Frame Rate
        info_layout.addWidget(QLabel("Frame Rate:"), 1, 0)
        self.framerate_label = QLabel("No file selected")
        self.framerate_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.framerate_label, 1, 1)
        
        # Bitrate
        info_layout.addWidget(QLabel("Bitrate:"), 2, 0)
        self.bitrate_label = QLabel("No file selected")
        self.bitrate_label.setStyleSheet("color: #666;")
        info_layout.addWidget(self.bitrate_label, 2, 1)
        
        layout.addLayout(info_layout)
        self.setLayout(layout)


class SettingsDialog(QDialog):
    """Settings dialog for themes and preferences"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.setWindowTitle("Settings")
        self.setFixedSize(500, 400)
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout()
        
        # Theme settings
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout()
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark Theme", "Light Theme", "Blue Theme", "Green Theme"])
        theme_layout.addWidget(QLabel("Select Theme:"))
        theme_layout.addWidget(self.theme_combo)
        
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)
        
        # Preview settings
        preview_group = QGroupBox("Preview Settings")
        preview_layout = QVBoxLayout()
        
        self.auto_update_checkbox = QCheckBox("Auto-update preview when settings change")
        self.auto_update_checkbox.setChecked(True)
        preview_layout.addWidget(self.auto_update_checkbox)
        
        self.preview_delay_spin = QSpinBox()
        self.preview_delay_spin.setRange(100, 3000)
        self.preview_delay_spin.setValue(1000)
        self.preview_delay_spin.setSuffix(" ms")
        preview_layout.addWidget(QLabel("Preview update delay:"))
        preview_layout.addWidget(self.preview_delay_spin)
        
        preview_group.setLayout(preview_layout)
        layout.addWidget(preview_group)
        
        # FFMPEG settings
        ffmpeg_group = QGroupBox("FFMPEG Settings")
        ffmpeg_layout = QVBoxLayout()
        
        self.temp_dir_label = QLabel(f"Temp directory: {self.parent.temp_dir}")
        ffmpeg_layout.addWidget(self.temp_dir_label)
        
        self.clear_temp_btn = QPushButton("Clear Temporary Files")
        self.clear_temp_btn.clicked.connect(self.clear_temp_files)
        ffmpeg_layout.addWidget(self.clear_temp_btn)
        
        ffmpeg_group.setLayout(ffmpeg_layout)
        layout.addWidget(ffmpeg_group)
        
        # Buttons
        button_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.cancel_btn = QPushButton("Cancel")
        self.save_btn.clicked.connect(self.save_settings)
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.cancel_btn)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
    def clear_temp_files(self):
        """Clear temporary files"""
        try:
            if os.path.exists(self.parent.temp_dir):
                shutil.rmtree(self.parent.temp_dir)
                self.parent.temp_dir = tempfile.mkdtemp()
                self.temp_dir_label.setText(f"Temp directory: {self.parent.temp_dir}")
                QMessageBox.information(self, "Success", "Temporary files cleared!")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to clear temp files: {e}")
    
    def save_settings(self):
        """Save settings and apply theme"""
        theme = self.theme_combo.currentText()
        self.parent.apply_theme(theme)
        
        # Save other settings
        old_auto_update = self.parent.auto_update_preview
        self.parent.auto_update_preview = self.auto_update_checkbox.isChecked()
        self.parent.preview_delay = self.preview_delay_spin.value()
        
        # Reconnect preview connections if auto-update setting changed
        if old_auto_update != self.parent.auto_update_preview:
            self.parent.setup_preview_connections()
        
        self.accept()


class FFMPEGMediaAnnihilatorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.input_file = None
        self.output_file = None
        self.media_type = None  # 'video' or 'audio'
        self.temp_dir = tempfile.mkdtemp()
        self.worker = None
        
        # Performance optimization variables
        self.preview_timer = None
        self.last_settings_hash = None
        self.is_updating_preview = False
        
        # Settings variables
        self.auto_update_preview = True
        self.preview_delay = 1000
        self.current_theme = "Dark Theme"
        
        self.setup_ui()
        self.setWindowTitle("FFMPEG Media Annihilator")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set window and application icon
        icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon512.png")
        app_icon = QIcon(icon_path)
        self.setWindowIcon(app_icon)
        QApplication.instance().setWindowIcon(app_icon)
        
        # Set application style
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QLabel {
                color: #ffffff;
                font-size: 12px;
            }
            QComboBox {
                background-color: #1e1e1e;
                border: 1px solid #444;
                padding: 5px;
                border-radius: 4px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #888;
                margin-right: 5px;
            }
            QCheckBox {
                spacing: 5px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #444;
                border-radius: 4px;
                background-color: #1e1e1e;
            }
            QCheckBox::indicator:checked {
                background-color: #4CAF50;
                border-color: #4CAF50;
            }
            QProgressBar {
                border: 1px solid #444;
                border-radius: 4px;
                text-align: center;
                background-color: #1e1e1e;
            }
            QProgressBar::chunk {
                background-color: #4CAF50;
                border-radius: 3px;
            }
        """)
        
    def setup_ui(self):
        self.setWindowTitle("FFMPEG Media Annihilator - Modern Edition")
        self.setGeometry(100, 100, 1200, 800)
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)
        
        # Left panel - Controls
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        left_panel.setMaximumWidth(500)
        
        # File selection
        file_group = ModernGroupBox("File Selection")
        file_layout = QVBoxLayout()
        
        # Input file
        input_layout = QHBoxLayout()
        self.input_btn = ModernButton("Select Input Media", "#2196F3")
        self.input_label = QLabel("No file selected")
        self.input_label.setStyleSheet("color: #888; padding: 5px;")
        input_layout.addWidget(self.input_btn)
        input_layout.addWidget(self.input_label)
        file_layout.addLayout(input_layout)
        
        # Output file
        output_layout = QHBoxLayout()
        self.output_btn = ModernButton("Select Output", "#FF9800")
        self.output_label = QLabel("Auto-generated")
        self.output_label.setStyleSheet("color: #888; padding: 5px;")
        output_layout.addWidget(self.output_btn)
        output_layout.addWidget(self.output_label)
        file_layout.addLayout(output_layout)
        
        file_group.setLayout(file_layout)
        left_layout.addWidget(file_group)
        
        # Video Effects
        video_group = ModernGroupBox("Video Effects")
        video_group.setObjectName("Video Effects")
        video_layout = QGridLayout()
        
        # Resolution scale
        video_layout.addWidget(QLabel("Resolution Scale:"), 0, 0)
        self.resolution_slider = QSlider(Qt.Orientation.Horizontal)
        self.resolution_slider.setRange(10, 100)
        self.resolution_slider.setValue(25)
        self.resolution_label = QLabel("25%")
        video_layout.addWidget(self.resolution_slider, 0, 1)
        video_layout.addWidget(self.resolution_label, 0, 2)
        
        # Blur
        video_layout.addWidget(QLabel("Blur Amount:"), 1, 0)
        self.blur_slider = QSlider(Qt.Orientation.Horizontal)
        self.blur_slider.setRange(0, 100)
        self.blur_slider.setValue(20)
        self.blur_label = QLabel("2.0")
        video_layout.addWidget(self.blur_slider, 1, 1)
        video_layout.addWidget(self.blur_label, 1, 2)
        
        # Compression
        video_layout.addWidget(QLabel("Compression (CRF):"), 2, 0)
        self.compression_slider = QSlider(Qt.Orientation.Horizontal)
        self.compression_slider.setRange(18, 51)
        self.compression_slider.setValue(35)
        self.compression_label = QLabel("35")
        video_layout.addWidget(self.compression_slider, 2, 1)
        video_layout.addWidget(self.compression_label, 2, 2)
        
        # Frame rate
        video_layout.addWidget(QLabel("Frame Rate:"), 3, 0)
        self.framerate_input = QDoubleSpinBox()
        self.framerate_input.setRange(0.1, 120.0)  # 0.1 to 120 fps
        self.framerate_input.setValue(30.0)  # Default 30 fps
        self.framerate_input.setSuffix(" fps")
        self.framerate_input.setDecimals(2)  # Allow 2 decimal places
        video_layout.addWidget(self.framerate_input, 3, 1, 1, 2)
        
        # Hue shift
        video_layout.addWidget(QLabel("Hue Shift:"), 4, 0)
        self.hue_slider = QSlider(Qt.Orientation.Horizontal)
        self.hue_slider.setRange(-180, 180)  # -180 to +180 degrees
        self.hue_slider.setValue(0)
        self.hue_label = QLabel("0°")
        video_layout.addWidget(self.hue_slider, 4, 1)
        video_layout.addWidget(self.hue_label, 4, 2)
        
        # Saturation
        video_layout.addWidget(QLabel("Saturation:"), 5, 0)
        self.saturation_slider = QSlider(Qt.Orientation.Horizontal)
        self.saturation_slider.setRange(0, 200)  # 0% to 200%
        self.saturation_slider.setValue(100)
        self.saturation_label = QLabel("100%")
        video_layout.addWidget(self.saturation_slider, 5, 1)
        video_layout.addWidget(self.saturation_label, 5, 2)
        
        # Media effects
        self.vhs_checkbox = QCheckBox("Add Media Artifacts")
        self.vhs_checkbox.setChecked(True)
        video_layout.addWidget(self.vhs_checkbox, 6, 0, 1, 3)
        
        video_group.setLayout(video_layout)
        left_layout.addWidget(video_group)
        
        # Audio Effects
        audio_group = ModernGroupBox("Audio Effects")
        audio_layout = QGridLayout()
        
        # Audio bitrate
        audio_layout.addWidget(QLabel("Audio Bitrate:"), 0, 0)
        self.audio_bitrate_combo = QComboBox()
        self.audio_bitrate_combo.addItems(["16k", "32k", "48k", "64k"])
        self.audio_bitrate_combo.setCurrentText("32k")
        audio_layout.addWidget(self.audio_bitrate_combo, 0, 1, 1, 2)
        
        # High pass
        audio_layout.addWidget(QLabel("High Pass (Hz):"), 1, 0)
        self.highpass_slider = QSlider(Qt.Orientation.Horizontal)
        self.highpass_slider.setRange(0, 1000)
        self.highpass_slider.setValue(300)
        self.highpass_label = QLabel("300Hz")
        audio_layout.addWidget(self.highpass_slider, 1, 1)
        audio_layout.addWidget(self.highpass_label, 1, 2)
        
        # Low pass
        audio_layout.addWidget(QLabel("Low Pass (Hz):"), 2, 0)
        self.lowpass_slider = QSlider(Qt.Orientation.Horizontal)
        self.lowpass_slider.setRange(1000, 8000)
        self.lowpass_slider.setValue(3000)
        self.lowpass_label = QLabel("3000Hz")
        audio_layout.addWidget(self.lowpass_slider, 2, 1)
        audio_layout.addWidget(self.lowpass_label, 2, 2)
        
        # Volume control (earrape capable)
        audio_layout.addWidget(QLabel("Volume:"), 4, 0)
        self.volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.volume_slider.setRange(0, 500)  # 0% to 500% (earrape levels!)
        self.volume_slider.setValue(100)
        audio_layout.addWidget(self.volume_slider, 4, 1)
        self.volume_label = QLabel("100%")
        audio_layout.addWidget(self.volume_label, 4, 2)
        
        # Earrape warning label (dynamic)
        self.earrape_label = QLabel("Warning: 200%+ may cause ear damage!")
        self.earrape_label.setStyleSheet("color: #ff6b6b; font-size: 11px;")
        self.earrape_label.hide()  # Initially hidden
        audio_layout.addWidget(self.earrape_label, 5, 0, 1, 3)
        
        # Pitch control
        audio_layout.addWidget(QLabel("Pitch:"), 6, 0)
        self.pitch_slider = QSlider(Qt.Orientation.Horizontal)
        self.pitch_slider.setRange(-12, 12)  # -12 to +12 semitones (one octave up/down)
        self.pitch_slider.setValue(0)
        self.pitch_label = QLabel("0 st")
        audio_layout.addWidget(self.pitch_slider, 6, 1)
        audio_layout.addWidget(self.pitch_label, 6, 2)
        
        # Speed control
        audio_layout.addWidget(QLabel("Speed:"), 7, 0)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(50, 200)  # 0.5x to 2x speed
        self.speed_slider.setValue(100)
        self.speed_label = QLabel("1.0x")
        audio_layout.addWidget(self.speed_slider, 7, 1)
        audio_layout.addWidget(self.speed_label, 7, 2)
        
        # Reverb effect
        self.reverb_checkbox = QCheckBox("Add Reverb Effect")
        audio_layout.addWidget(self.reverb_checkbox, 8, 0, 1, 3)
        
        # Distortion effect
        self.distortion_checkbox = QCheckBox("Add Distortion")
        audio_layout.addWidget(self.distortion_checkbox, 9, 0, 1, 3)
        
        # Sample rate
        audio_layout.addWidget(QLabel("Sample Rate:"), 10, 0)
        self.sample_rate_combo = QComboBox()
        self.sample_rate_combo.addItems(["48000", "44100", "22050", "11025", "8000"])
        self.sample_rate_combo.setCurrentText("22050")  # Default to vintage quality
        audio_layout.addWidget(self.sample_rate_combo, 10, 1, 1, 2)
        
        # Enable audio
        self.enable_audio_checkbox = QCheckBox("Enable Audio Processing")
        self.enable_audio_checkbox.setChecked(True)
        audio_layout.addWidget(self.enable_audio_checkbox, 11, 0, 1, 3)
        
        # Enhanced audio processing (for video files)
        self.enhanced_audio_checkbox = QCheckBox("Enhanced Audio Processing (Extreme Mode)")
        self.enhanced_audio_checkbox.setChecked(False)
        self.enhanced_audio_checkbox.setToolTip("Uses multi-stage pipeline for maximum audio effect intensity (video files only)")
        audio_layout.addWidget(self.enhanced_audio_checkbox, 12, 0, 1, 3)
        
        # Metadata annihilation type
        audio_layout.addWidget(QLabel("Metadata Annihilation:"), 13, 0)
        self.metadata_annihilation_combo = QComboBox()
        self.metadata_annihilation_combo.addItems(["Nuke", "Corrupt", "Random", "Disabled"])
        self.metadata_annihilation_combo.setCurrentText("Nuke")
        self.metadata_annihilation_combo.setToolTip("Nuke: Remove all metadata | Corrupt: Add invalid values | Random: Add fake random metadata")
        audio_layout.addWidget(self.metadata_annihilation_combo, 13, 1, 1, 2)
        
        audio_group.setLayout(audio_layout)
        left_layout.addWidget(audio_group)
        
        # Action buttons
        action_layout = QHBoxLayout()
        self.process_btn = ModernButton("Process Media", "primary")
        self.preview_btn = ModernButton("Update Preview", "secondary")
        self.settings_btn = ModernButton("Settings", "settings")
        self.preview_btn.setEnabled(False)  # Enable only when file is selected
        action_layout.addWidget(self.process_btn)
        action_layout.addWidget(self.preview_btn)
        action_layout.addWidget(self.settings_btn)
        left_layout.addLayout(action_layout)
        
        # Progress
        progress_group = ModernGroupBox("Progress")
        progress_layout = QVBoxLayout()
        self.progress_bar = QProgressBar()
        self.progress_label = QLabel("Ready")
        self.preview_status_label = QLabel("Preview: Ready")
        self.preview_status_label.setStyleSheet("color: #888; font-size: 11px;")
        progress_layout.addWidget(self.progress_label)
        progress_layout.addWidget(self.progress_bar)
        progress_layout.addWidget(self.preview_status_label)
        progress_group.setLayout(progress_layout)
        left_layout.addWidget(progress_group)
        
        left_layout.addStretch()
        
        # Right panel - Preview and Info
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_panel.setLayout(right_layout)
        
        # Splitter for original and processed sections
        main_splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Original section (preview + info)
        original_section = QWidget()
        original_layout = QVBoxLayout()
        original_section.setLayout(original_layout)
        
        # Original preview
        original_preview_group = ModernGroupBox("Original Preview")
        original_preview_layout = QVBoxLayout()
        self.original_preview_widget = VideoPreviewWidget()
        original_preview_layout.addWidget(self.original_preview_widget)
        original_preview_group.setLayout(original_preview_layout)
        original_layout.addWidget(original_preview_group)
        
        # Original info
        self.original_info = VideoInfoWidget("Original Video")
        original_layout.addWidget(self.original_info)
        
        # Processed section (preview + info)
        processed_section = QWidget()
        processed_layout = QVBoxLayout()
        processed_section.setLayout(processed_layout)
        
        # Processed preview
        processed_preview_group = ModernGroupBox("Processed Preview")
        processed_preview_layout = QVBoxLayout()
        self.processed_preview_widget = VideoPreviewWidget()
        processed_preview_layout.addWidget(self.processed_preview_widget)
        processed_preview_group.setLayout(processed_preview_layout)
        processed_layout.addWidget(processed_preview_group)
        
        # Processed info
        self.processed_info = VideoInfoWidget("Processed Video")
        processed_layout.addWidget(self.processed_info)
        
        # Add sections to main splitter
        main_splitter.addWidget(original_section)
        main_splitter.addWidget(processed_section)
        main_splitter.setSizes([600, 600])
        
        right_layout.addWidget(main_splitter)
        
        # Add panels to main layout
        main_layout.addWidget(left_panel)
        main_layout.addWidget(right_panel)
        
        # Set stretch factors
        main_layout.setStretch(0, 1)
        main_layout.setStretch(1, 1)
        
        # Connect signals
        self.connect_signals()
        
    def connect_signals(self):
        """Connect all signals and slots"""
        # File buttons
        self.input_btn.clicked.connect(self.select_input_file)
        self.output_btn.clicked.connect(self.select_output_file)
        
        # Action buttons
        self.process_btn.clicked.connect(self.process_media_enhanced)
        self.preview_btn.clicked.connect(self.manual_update_preview)
        self.settings_btn.clicked.connect(self.open_settings)
        
        # Conditional preview updates when settings change
        self.setup_preview_connections()
        
        # Sliders
        self.resolution_slider.valueChanged.connect(self.update_resolution_label)
        self.blur_slider.valueChanged.connect(self.update_blur_label)
        self.compression_slider.valueChanged.connect(self.update_compression_label)
        self.highpass_slider.valueChanged.connect(self.update_highpass_label)
        self.lowpass_slider.valueChanged.connect(self.update_lowpass_label)
        self.volume_slider.valueChanged.connect(self.update_volume_label)
        self.pitch_slider.valueChanged.connect(self.update_pitch_label)
        self.speed_slider.valueChanged.connect(self.update_speed_label)
        self.hue_slider.valueChanged.connect(self.update_hue_label)
        self.saturation_slider.valueChanged.connect(self.update_saturation_label)
        
        # Settings changes
        self.resolution_slider.valueChanged.connect(self.update_processed_specs)
        self.framerate_input.valueChanged.connect(self.update_processed_specs)
        self.audio_bitrate_combo.currentTextChanged.connect(self.update_processed_specs)
        
    def update_resolution_label(self, value):
        self.resolution_label.setText(f"{value}%")
        
    def update_blur_label(self, value):
        self.blur_label.setText(f"{value/10:.1f}")
        
    def update_compression_label(self, value):
        self.compression_label.setText(str(value))
        
    def update_highpass_label(self, value):
        self.highpass_label.setText(f"{value}Hz")
        
    def update_lowpass_label(self, value):
        self.lowpass_label.setText(f"{value}Hz")
        
    def update_volume_label(self, value):
        self.volume_label.setText(f"{value}%")
        
        # Show earrape warning when volume is 200% or higher
        if value >= 200:
            self.earrape_label.show()
        else:
            self.earrape_label.hide()
    
    def update_pitch_label(self, value):
        self.pitch_label.setText(f"{value} st")
    
    def update_speed_label(self, value):
        self.speed_label.setText(f"{value/100:.1f}x")
    
    def update_hue_label(self, value):
        self.hue_label.setText(f"{value}°")
    
    def update_saturation_label(self, value):
        self.saturation_label.setText(f"{value}%")
        
            
    def setup_preview_connections(self):
        """Setup preview connections based on auto-update setting"""
        if self.auto_update_preview:
            self.resolution_slider.valueChanged.connect(self.debounced_update_previews)
            self.blur_slider.valueChanged.connect(self.debounced_update_previews)
            self.compression_slider.valueChanged.connect(self.debounced_update_previews)
            self.framerate_input.valueChanged.connect(self.debounced_update_previews)
            self.audio_bitrate_combo.currentTextChanged.connect(self.debounced_update_previews)
            self.highpass_slider.valueChanged.connect(self.debounced_update_previews)
            self.lowpass_slider.valueChanged.connect(self.debounced_update_previews)
            self.volume_slider.valueChanged.connect(self.debounced_update_previews)
            self.pitch_slider.valueChanged.connect(self.debounced_update_previews)
            self.speed_slider.valueChanged.connect(self.debounced_update_previews)
            self.hue_slider.valueChanged.connect(self.debounced_update_previews)
            self.saturation_slider.valueChanged.connect(self.debounced_update_previews)
            self.sample_rate_combo.currentTextChanged.connect(self.debounced_update_previews)
            self.vhs_checkbox.stateChanged.connect(self.debounced_update_previews)
            self.enable_audio_checkbox.stateChanged.connect(self.debounced_update_previews)
            self.enhanced_audio_checkbox.stateChanged.connect(self.debounced_update_previews)
            self.metadata_annihilation_combo.currentTextChanged.connect(self.debounced_update_previews)
    
    def manual_update_preview(self):
        """Manually trigger preview update"""
        if self.input_file:
            self.last_settings_hash = None  # Force update
            self.update_previews()
    
    def open_settings(self):
        """Open settings dialog"""
        dialog = SettingsDialog(self)
        dialog.theme_combo.setCurrentText(self.current_theme)
        dialog.auto_update_checkbox.setChecked(self.auto_update_preview)
        dialog.preview_delay_spin.setValue(self.preview_delay)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            self.current_theme = dialog.theme_combo.currentText()
            self.apply_theme(self.current_theme)
    
    def apply_theme(self, theme_name):
        """Apply selected theme"""
        themes = {
            "Dark Theme": {
                "bg": "#2b2b2b",
                "widget_bg": "#3c3c3c",
                "text": "#ffffff",
                "button": "#4a4a4a",
                "button_hover": "#5a5a5a",
                "group": "#404040",
                "border": "#555555"
            },
            "Light Theme": {
                "bg": "#f5f5f5",
                "widget_bg": "#ffffff",
                "text": "#333333",
                "button": "#2196F3",
                "button_hover": "#1976D2",
                "group": "#f0f0f0",
                "border": "#cccccc"
            },
            "Blue Theme": {
                "bg": "#1a237e",
                "widget_bg": "#283593",
                "text": "#ffffff",
                "button": "#5c6bc0",
                "button_hover": "#7986cb",
                "group": "#303f9f",
                "border": "#5c6bc0"
            },
            "Green Theme": {
                "bg": "#1b5e20",
                "widget_bg": "#2e7d32",
                "text": "#ffffff",
                "button": "#66bb6a",
                "button_hover": "#81c784",
                "group": "#388e3c",
                "border": "#66bb6a"
            }
        }
        
        theme = themes.get(theme_name, themes["Dark Theme"])
        
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {theme['bg']};
            }}
            QWidget {{
                background-color: {theme['widget_bg']};
                color: {theme['text']};
                font-family: 'Segoe UI', Arial, sans-serif;
            }}
            QGroupBox {{
                font-weight: bold;
                border: 2px solid {theme['border']};
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: {theme['group']};
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }}
            QPushButton {{
                background-color: {theme['button']};
                border: none;
                padding: 8px 16px;
                border-radius: 6px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {theme['button_hover']};
            }}
            QPushButton:pressed {{
                background-color: {theme['border']};
            }}
            QSlider::groove:horizontal {{
                border: 1px solid {theme['border']};
                height: 6px;
                background: {theme['button']};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {theme['border']};
                border: 1px solid {theme['text']};
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QProgressBar {{
                border: 1px solid {theme['border']};
                border-radius: 6px;
                text-align: center;
                background-color: {theme['button']};
            }}
            QProgressBar::chunk {{
                background-color: #4CAF50;
                border-radius: 5px;
            }}
            QComboBox, QSpinBox {{
                background-color: {theme['button']};
                border: 1px solid {theme['border']};
                border-radius: 4px;
                padding: 4px;
            }}
            QComboBox::drop-down {{
                border: none;
            }}
            QComboBox::down-arrow {{
                image: none;
                border-left: 4px solid transparent;
                border-right: 4px solid transparent;
                border-top: 4px solid {theme['text']};
            }}
            QCheckBox::indicator {{
                background-color: {theme['button']};
                border: 1px solid {theme['border']};
                border-radius: 3px;
                width: 14px;
                height: 14px;
            }}
            QCheckBox::indicator:checked {{
                background-color: #4CAF50;
            }}
        """)
        
        self.current_theme = theme_name
        self.update_all_buttons()
    
    def update_all_buttons(self):
        """Update all ModernButton instances to use new theme"""
        buttons = self.findChildren(ModernButton)
        for button in buttons:
            button.update_style()
    
    def select_input_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Select Media File", "",
            "Media Files (*.mp4 *.avi *.mov *.mkv *.webm *.flv *.mp3 *.wav *.ogg *.flac *.aac);;Video Files (*.mp4 *.avi *.mov *.mkv *.webm *.flv);;Audio Files (*.mp3 *.wav *.ogg *.flac *.aac);;All Files (*)"
        )
        if file_path:
            self.input_file = file_path
            self.input_label.setText(Path(file_path).name)
            
            # Detect media type
            self.detect_media_type(file_path)
            
            # Always update output file when input changes to ensure correct extension
            input_path = Path(file_path)
            # Use appropriate extension based on media type
            ext = '.mp3' if self.media_type == 'audio' else '.mp4'
            new_output_file = str(input_path.parent / f"{input_path.stem}_annihilated{ext}")
            
            # Only update if output file is empty or has wrong extension
            if not self.output_file or not Path(self.output_file).suffix.lower() == ext.lower():
                self.output_file = new_output_file
                self.output_label.setText(Path(self.output_file).name)
            
            # Enable preview button
            self.preview_btn.setEnabled(True)
            
            # Reset settings hash to force initial preview
            self.last_settings_hash = None
            
            self.update_video_info_display()
            self.update_ui_for_media_type()
            
    def detect_media_type(self, file_path):
        """Detect if the file is video or audio based on extension and ffprobe"""
        file_ext = Path(file_path).suffix.lower()
        audio_extensions = {'.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a'}
        video_extensions = {'.mp4', '.avi', '.mov', '.mkv', '.webm', '.flv', '.wmv'}
        
        old_media_type = self.media_type
        
        if file_ext in audio_extensions:
            self.media_type = 'audio'
        elif file_ext in video_extensions:
            self.media_type = 'video'
        else:
            # Use ffprobe to detect media type if extension is unknown
            try:
                cmd = ["ffprobe", "-v", "quiet", "-select_streams", "v:0", "-show_entries", "stream=codec_type", "-of", "csv=p=0", file_path]
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                if result.stdout.strip():
                    self.media_type = 'video'
                else:
                    self.media_type = 'audio'
            except:
                # Fallback to audio if detection fails
                self.media_type = 'audio'
        
        # Debug output for media type changes
        if old_media_type != self.media_type:
            print(f"Media type changed from {old_media_type} to {self.media_type} for {Path(file_path).name}")
    
    def update_ui_for_media_type(self):
        """Update UI based on media type - hide video effects and data comparison for audio files"""
        video_group = self.findChild(ModernGroupBox, "Video Effects")
        
        if self.media_type == 'audio':
            # Hide video effects group completely for audio files
            if video_group:
                video_group.hide()
            
            # Hide data comparison section for audio files
            if hasattr(self, 'original_info') and hasattr(self, 'processed_info'):
                self.original_info.hide()
                self.processed_info.hide()
            
            # Hide enhanced audio checkbox (only for video files)
            if hasattr(self, 'enhanced_audio_checkbox'):
                self.enhanced_audio_checkbox.hide()
            
            # Show pitch and speed controls for audio files
            if hasattr(self, 'pitch_slider'):
                self.pitch_slider.show()
            if hasattr(self, 'pitch_label'):
                self.pitch_label.show()
            # Show the "Pitch:" label
            pitch_labels = [widget for widget in self.findChildren(QLabel) if widget.text() == "Pitch:"]
            for label in pitch_labels:
                label.show()
            
            if hasattr(self, 'speed_slider'):
                self.speed_slider.show()
            if hasattr(self, 'speed_label'):
                self.speed_label.show()
            # Show the "Speed:" label
            speed_labels = [widget for widget in self.findChildren(QLabel) if widget.text() == "Speed:"]
            for label in speed_labels:
                label.show()
            
            # Update button text to reflect audio processing
            self.input_btn.setText("Select Input Media")
            
        else:  # video
            # Show video effects group for video files
            if video_group:
                video_group.show()
                video_group.setEnabled(True)
                video_group.setStyleSheet("")
            
            # Show data comparison section for video files
            if hasattr(self, 'original_info') and hasattr(self, 'processed_info'):
                self.original_info.show()
                self.processed_info.show()
            
            # Show enhanced audio checkbox for video files
            if hasattr(self, 'enhanced_audio_checkbox'):
                self.enhanced_audio_checkbox.show()
            
            # Hide pitch and speed controls for video files (prevent A/V sync issues)
            if hasattr(self, 'pitch_slider'):
                self.pitch_slider.hide()
            if hasattr(self, 'pitch_label'):
                self.pitch_label.hide()
            # Hide the "Pitch:" label
            pitch_labels = [widget for widget in self.findChildren(QLabel) if widget.text() == "Pitch:"]
            for label in pitch_labels:
                label.hide()
            
            if hasattr(self, 'speed_slider'):
                self.speed_slider.hide()
            if hasattr(self, 'speed_label'):
                self.speed_label.hide()
            # Hide the "Speed:" label
            speed_labels = [widget for widget in self.findChildren(QLabel) if widget.text() == "Speed:"]
            for label in speed_labels:
                label.hide()
            
            # Update button text to reflect video processing
            self.input_btn.setText("Select Input Media")
            
    def select_output_file(self):
        if not self.input_file:
            QMessageBox.warning(self, "Warning", "Please select an input file first.")
            return
            
        input_path = Path(self.input_file)
        
        # Use appropriate default extension and dialog based on media type
        if self.media_type == 'audio':
            default_name = f"{input_path.stem}_annihilated.mp3"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Processed Audio", 
                str(input_path.parent / default_name),
                "MP3 Files (*.mp3);;WAV Files (*.wav);;AAC Files (*.aac);;All Files (*)"
            )
        else:
            default_name = f"{input_path.stem}_annihilated.mp4"
            file_path, _ = QFileDialog.getSaveFileName(
                self, "Save Processed Video", 
                str(input_path.parent / default_name),
                "MP4 Files (*.mp4);;AVI Files (*.avi);;MOV Files (*.mov);;All Files (*)"
            )
        if file_path:
            self.output_file = file_path
            self.output_label.setText(Path(file_path).name)
            
    def get_video_info(self, video_path):
        """Get video metadata using FFMPEG probe"""
        try:
            cmd = [
                "ffprobe", "-v", "quiet", "-print_format", "json",
                "-show_format", "-show_streams", video_path
            ]
            result = subprocess.run(cmd, capture_output=True, text=True, check=True)
            probe_data = json.loads(result.stdout)
            
            video_stream = None
            for stream in probe_data.get('streams', []):
                if stream.get('codec_type') == 'video' and not video_stream:
                    video_stream = stream
                    break
            
            info = {
                'resolution': 'Unknown',
                'frame_rate': 'Unknown',
                'bitrate': 'Unknown'
            }
            
            if video_stream:
                width = video_stream.get('width')
                height = video_stream.get('height')
                if width and height:
                    info['resolution'] = f"{width}x{height}"
                
                r_frame_rate = video_stream.get('r_frame_rate', '0/1')
                if '/' in r_frame_rate:
                    num, den = r_frame_rate.split('/')
                    try:
                        fps = float(num) / float(den)
                        info['frame_rate'] = f"{fps:.2f}"
                    except:
                        pass
            
            format_info = probe_data.get('format', {})
            bitrate = format_info.get('bit_rate') or video_stream.get('bit_rate')
            if bitrate:
                try:
                    bitrate_kbps = int(bitrate) // 1000
                    info['bitrate'] = f"{bitrate_kbps} kb/s"
                except:
                    pass
            
            return info
            
        except (subprocess.CalledProcessError, json.JSONDecodeError, KeyError):
            return {
                'resolution': 'Unknown',
                'frame_rate': 'Unknown',
                'bitrate': 'Unknown'
            }
            
    def calculate_processed_specs(self):
        """Calculate processed video specifications"""
        if not self.input_file:
            return {
                'resolution': 'Unknown',
                'frame_rate': 'Unknown',
                'bitrate': 'Unknown'
            }
        
        original_info = self.get_video_info(self.input_file)
        
        processed = {
            'resolution': 'Unknown',
            'frame_rate': 'Unknown',
            'bitrate': self.audio_bitrate_combo.currentText()
        }
        
        if original_info['resolution'] != 'Unknown':
            try:
                width, height = map(int, original_info['resolution'].split('x'))
                scale = self.resolution_slider.value() / 100.0
                new_width = int(width * scale)
                new_height = int(height * scale)
                processed['resolution'] = f"{new_width}x{new_height}"
            except:
                processed['resolution'] = 'Calculated'
        
        processed['frame_rate'] = f"{self.framerate_input.value():.2f} fps"
        
        return processed
        
    def get_settings_hash(self):
        """Calculate hash of current settings to detect changes"""
        settings = f"{self.resolution_slider.value()}{self.blur_slider.value()}{self.compression_slider.value()}{self.framerate_input.value()}{self.audio_bitrate_combo.currentText()}{self.highpass_slider.value()}{self.lowpass_slider.value()}{self.volume_slider.value()}{self.pitch_slider.value()}{self.speed_slider.value()}{self.hue_slider.value()}{self.saturation_slider.value()}{self.sample_rate_combo.currentText()}{self.vhs_checkbox.isChecked()}{self.enable_audio_checkbox.isChecked()}{self.enhanced_audio_checkbox.isChecked()}{self.reverb_checkbox.isChecked()}{self.distortion_checkbox.isChecked()}{self.metadata_annihilation_combo.currentText()}"
        return hash(settings)
    
    def debounced_update_previews(self):
        """Debounced preview update to prevent excessive FFMPEG calls"""
        if self.is_updating_preview:
            return
        
        # Cancel existing timer
        if self.preview_timer:
            self.preview_timer.stop()
            self.preview_timer = None
        
        # Check if settings actually changed
        current_hash = self.get_settings_hash()
        if current_hash == self.last_settings_hash:
            return
        
        self.last_settings_hash = current_hash
        
        # Start new timer with configurable delay
        self.preview_timer = QTimer()
        self.preview_timer.setSingleShot(True)
        self.preview_timer.timeout.connect(self.update_previews)
        self.preview_timer.start(self.preview_delay)  # Use configurable delay
    
    def update_previews(self):
        """Update both previews when settings change"""
        if self.is_updating_preview or not self.input_file:
            return
        
        self.is_updating_preview = True
        self.preview_status_label.setText("Preview: Updating...")
        
        # Show original preview immediately (fast)
        self.show_original_preview()
        
        # Show effects preview with delay (slow)
        QTimer.singleShot(200, self.show_effects_preview)
        
        # Reset flag after delay
        QTimer.singleShot(1000, self.reset_preview_status)
    
    def reset_preview_status(self):
        """Reset preview status"""
        self.is_updating_preview = False
        self.preview_status_label.setText("Preview: Ready")
    
    def update_video_info_display(self):
        """Update video information displays"""
        if self.input_file:
            # Original info
            original_info = self.get_video_info(self.input_file)
            self.original_info.resolution_label.setText(original_info['resolution'])
            self.original_info.framerate_label.setText(original_info['frame_rate'])
            self.original_info.bitrate_label.setText(original_info['bitrate'])
            
            # Processed info
            self.update_processed_specs()
            
            # Show previews when file is selected
            self.update_previews()
        else:
            # Clear all
            for widget in [self.original_info, self.processed_info]:
                widget.resolution_label.setText("No file selected")
                widget.framerate_label.setText("No file selected")
                widget.bitrate_label.setText("No file selected")
            
            # Clear previews
            for i, frame in enumerate(self.original_preview_widget.preview_frames):
                frame.clear()
                frame.setText(f"Frame {i+1}\nNo Preview")
            for i, frame in enumerate(self.processed_preview_widget.preview_frames):
                frame.clear()
                frame.setText(f"Frame {i+1}\nNo Preview")
                
    def update_processed_specs(self):
        """Update processed video specs"""
        if self.input_file:
            processed_info = self.calculate_processed_specs()
            self.processed_info.resolution_label.setText(processed_info['resolution'])
            self.processed_info.framerate_label.setText(processed_info['frame_rate'])
            self.processed_info.bitrate_label.setText(processed_info['bitrate'])
            
    def add_metadata_annihilation(self, cmd):
        """Add metadata annihilation parameters to FFmpeg command"""
        # Validate metadata combo box exists
        if not hasattr(self, 'metadata_annihilation_combo'):
            return
            
        metadata_type = self.metadata_annihilation_combo.currentText()
        
        if metadata_type == "Nuke":
            cmd.extend(["-map_metadata", "-1"])  # Remove all metadata
        elif metadata_type == "Corrupt":
            # Add invalid/corrupt metadata
            cmd.extend([
                "-metadata", "title=@@@@@@@@@@@@@@@@@@@@",
                "-metadata", "artist=&&&&&&&&&&&&&&&&&&&&",
                "-metadata", "album_artist=))))))))))))))))))))",
                "-metadata", "album=####################",
                "-metadata", "year=((((((((((((((((((((",
                "-metadata", "genre=********************" 
            ])
        elif metadata_type == "Random":
            # Add random fake metadata
            fake_titles = ["Static Noise", "Data Stream", "Binary Dreams", "Glitch Symphony", "Error Melody"]
            fake_artists = ["Anonymous", "Unknown Source", "Data Ghost", "Signal Lost", "Void Walker"]
            fake_albums = ["Lost Files", "Corrupted Data", "Digital Ruins", "Broken Circuits", "System Failure"]
            cmd.extend([
                "-metadata", f"title={random.choice(fake_titles)}",
                "-metadata", f"artist={random.choice(fake_artists)}",
                "-metadata", f"album_artist={random.choice(fake_artists)}",
                "-metadata", f"album={random.choice(fake_albums)}",
                "-metadata", f"year={random.randint(1970, 2024)}",
                "-metadata", f"track={random.randint(1, 99)}"
            ])
            
    def build_ffmpeg_command(self):
        """Build FFMPEG command with current settings"""
        if not self.input_file or not self.output_file:
            return None
            
        cmd = ["ffmpeg", "-i", self.input_file]
        
        # Handle audio-only files
        if self.media_type == 'audio':
            # Audio filters for audio-only files
            if self.enable_audio_checkbox.isChecked():
                audio_filters = []
                
                # Volume control (always apply if changed) with explicit stereo
                volume = self.volume_slider.value() / 100.0
                if volume != 1.0:
                    audio_filters.append(f"volume={volume},pan=stereo|c0=c0|c1=c1")
                
                # High pass filter
                highpass_freq = self.highpass_slider.value()
                if highpass_freq > 0:
                    audio_filters.append(f"highpass=f={highpass_freq}")
                
                # Low pass filter
                lowpass_freq = self.lowpass_slider.value()
                if lowpass_freq > 0:
                    audio_filters.append(f"lowpass=f={lowpass_freq}")
                
                # Pitch control (semitones)
                pitch_shift = self.pitch_slider.value()
                if pitch_shift != 0:
                    audio_filters.append(f"asetrate=r=44100*2^({pitch_shift}/12)")
                
                # Speed control (tempo)
                speed_factor = self.speed_slider.value() / 100.0
                if speed_factor != 1.0:
                    audio_filters.append(f"atempo={speed_factor}")
                
                # Add effects that don't break sync
                try:
                    # Reverb effect (safe for sync) - more pronounced echo, ensure stereo
                    if self.reverb_checkbox.isChecked():
                        audio_filters.append("aecho=0.9:0.85:60:0.3")
                    
                    # Distortion effect (safe for sync) - ensure stereo
                    if self.distortion_checkbox.isChecked():
                        audio_filters.append("acrusher=bits=6:level_in=2:level_out=2")
                        
                                        
                except Exception:
                    # Skip complex effects if they cause issues
                    pass
                
                # Apply audio filters if any
                if audio_filters:
                    cmd.extend(["-af", ",".join(audio_filters)])
            
            # Audio-only output settings
            output_path = self.output_file
            if not output_path.lower().endswith(('.mp3', '.wav', '.aac')):
                output_path = str(Path(output_path).with_suffix('.mp3'))
            
            # Determine codec and quality based on output extension
            if output_path.lower().endswith('.wav'):
                # WAV output - use PCM codec, no bitrate compression
                cmd.extend([
                    "-vn",  # No video
                    "-c:a", "pcm_s16le",  # Standard WAV codec
                    "-ar", self.sample_rate_combo.currentText(),  # Sample rate only
                ])
                
                # Handle metadata annihilation
                self.add_metadata_annihilation(cmd)
                cmd.extend(["-y", output_path])
            elif output_path.lower().endswith('.aac'):
                # AAC output - use AAC codec with appropriate bitrate
                cmd.extend([
                    "-vn",  # No video
                    "-c:a", "aac",
                    "-ar", self.sample_rate_combo.currentText(),
                    "-b:a", self.audio_bitrate_combo.currentText(),  # Use selected bitrate
                ])
                
                # Handle metadata annihilation
                self.add_metadata_annihilation(cmd)
                cmd.extend(["-y", output_path])
            else:  # Default to MP3
                cmd.extend([
                    "-vn",  # No video
                    "-c:a", "libmp3lame",
                    "-ar", self.sample_rate_combo.currentText(),
                    "-q:a", "2",  # MP3 quality
                ])
                
                # Handle metadata annihilation
                self.add_metadata_annihilation(cmd)
                cmd.extend(["-y", output_path])
            
        else:  # Video files
            # Video filters
            video_filters = []
            
            # Scale
            scale = self.resolution_slider.value() / 100.0
            video_filters.append(f"scale=iw*{scale}:ih*{scale}:flags=neighbor")
            
            # Blur
            blur_amount = self.blur_slider.value() / 10.0
            if blur_amount > 0:
                video_filters.append(f"gblur=sigma={blur_amount}")
            
            # Frame rate
            frame_rate = self.framerate_input.value()
            video_filters.append(f"fps={frame_rate}")
            
            # Hue shift
            hue_shift = self.hue_slider.value()
            if hue_shift != 0:
                video_filters.append(f"hue=h={hue_shift}")
            
            # Saturation (will be combined with VHS effects if needed)
            saturation = self.saturation_slider.value() / 100.0
            
            # Media effects
            if self.vhs_checkbox.isChecked():
                # Combine saturation with VHS effects
                vhs_saturation = saturation * 0.8  # VHS effect reduces saturation to 80%
                video_filters.extend([
                    "noise=alls=10:allf=t",
                    f"eq=contrast=1.1:brightness=0.05:saturation={vhs_saturation}",
                    "format=yuv420p,curves=master='0/0 0.2/0.1 0.4/0.3 0.6/0.7 0.8/0.9 1/1'"
                ])
            elif saturation != 1.0:
                # Apply saturation only if VHS is not enabled
                video_filters.append(f"eq=saturation={saturation}")
            
            if video_filters:
                cmd.extend(["-vf", ",".join(video_filters)])
            
            # Audio filters
            if self.enable_audio_checkbox.isChecked():
                audio_filters = []
                
                # Volume control (always apply if changed) with explicit stereo
                volume = self.volume_slider.value() / 100.0
                if volume != 1.0:
                    audio_filters.append(f"volume={volume},pan=stereo|c0=c0|c1=c1")
                
                # High pass filter
                highpass_freq = self.highpass_slider.value()
                if highpass_freq > 0:
                    audio_filters.append(f"highpass=f={highpass_freq}")
                
                # Low pass filter
                lowpass_freq = self.lowpass_slider.value()
                if lowpass_freq > 0:
                    audio_filters.append(f"lowpass=f={lowpass_freq}")
                
                # Pitch control (semitones)
                pitch_shift = self.pitch_slider.value()
                if pitch_shift != 0:
                    audio_filters.append(f"asetrate=r=44100*2^({pitch_shift}/12)")
                
                # Speed control (tempo)
                speed_factor = self.speed_slider.value() / 100.0
                if speed_factor != 1.0:
                    audio_filters.append(f"atempo={speed_factor}")
                
                # Add effects that don't break sync
                try:
                    # Reverb effect (safe for sync) - more pronounced echo, ensure stereo
                    if self.reverb_checkbox.isChecked():
                        audio_filters.append("aecho=0.9:0.85:60:0.3")
                    
                    # Distortion effect (safe for sync) - ensure stereo
                    if self.distortion_checkbox.isChecked():
                        audio_filters.append("acrusher=bits=6:level_in=2:level_out=2")
                        
                                        
                except Exception:
                    # Skip complex effects if they cause issues
                    pass
                
                # Apply audio filters if any
                if audio_filters:
                    cmd.extend(["-af", ",".join(audio_filters)])
                
                # Audio quality settings
                cmd.extend(["-ar", self.sample_rate_combo.currentText()])
                cmd.extend(["-b:a", self.audio_bitrate_combo.currentText()])
            
            # Video compression
            cmd.extend(["-crf", str(self.compression_slider.value())])
            
            # Output settings
            output_path = self.output_file
            if not output_path.lower().endswith('.mp4'):
                output_path = str(Path(output_path).with_suffix('.mp4'))
            
            cmd.extend([
                "-c:v", "libx264",
                "-preset", "fast",
                "-r", str(frame_rate),
                "-c:a", "aac",
            ])
            
            # Handle metadata annihilation for video files
            self.add_metadata_annihilation(cmd)
            cmd.extend(["-y", output_path])
        
        return cmd
        
    def preview_settings(self):
        """Show FFMPEG command preview"""
        cmd = self.build_ffmpeg_command()
        if cmd:
            command_text = " ".join(cmd)
            QMessageBox.information(self, "FFMPEG Command", command_text)
            
    def process_video(self):
        """Process video with FFMPEG"""
        if not self.input_file or not self.output_file:
            QMessageBox.warning(self, "Warning", "Please select input and output files.")
            return
        
        cmd = self.build_ffmpeg_command()
        if cmd:
            # Show command for debugging
            print("FFMPEG Command:", " ".join(cmd))
            
            self.process_btn.setEnabled(False)
            self.progress_bar.setRange(0, 100)  # Set progress range
            self.progress_bar.setValue(0)
            self.progress_label.setText("Starting...")
            
            self.worker = FFmpegWorker(cmd)
            self.worker.progress_updated.connect(self.update_progress)
            self.worker.finished.connect(self.processing_finished_with_fallback)
            self.worker.start()
    
    def processing_finished_with_fallback(self, success, error_msg):
        """Handle processing completion with fallback option"""
        if not success and self.enable_audio_checkbox.isChecked():
            # Try again with basic audio processing only
            print("Complex audio processing failed, trying basic audio...")
            self.progress_label.setText("Retrying with basic audio...")
            
            # Temporarily disable complex effects
            original_reverb = self.reverb_checkbox.isChecked()
            original_distortion = self.distortion_checkbox.isChecked()
            
            self.reverb_checkbox.setChecked(False)
            self.distortion_checkbox.setChecked(False)
            
            cmd = self.build_ffmpeg_command_sync_safe()
            if cmd:
                print("Fallback FFMPEG Command:", " ".join(cmd))
                self.worker = FFmpegWorker(cmd)
                self.worker.progress_updated.connect(self.update_progress)
                self.worker.finished.connect(lambda success, msg: self.processing_finished_final(success, msg, original_reverb, original_distortion))
                self.worker.start()
                return
            else:
                # Restore settings
                self.reverb_checkbox.setChecked(original_reverb)
                self.distortion_checkbox.setChecked(original_distortion)
        
        self.processing_finished(success, error_msg)
    
    def build_ffmpeg_command_sync_safe(self):
        """Build FFMPEG command with sync-safe audio processing"""
        return self.build_ffmpeg_command()  # Use the updated main method
    
    def process_media_enhanced(self):
        """Process media using enhanced multi-stage pipeline for maximum audio intensity"""
        if not self.input_file or not self.output_file:
            QMessageBox.warning(self, "Warning", "Please select input and output files.")
            return
        
        # Only use enhanced mode for video files with audio enabled
        if self.media_type != 'video' or not self.enable_audio_checkbox.isChecked() or not self.enhanced_audio_checkbox.isChecked():
            # Fall back to regular processing
            self.process_video()
            return
        
        try:
            # Step 1: Extract audio from video
            temp_audio = os.path.join(self.temp_dir, "extracted_audio.wav")
            self.progress_label.setText("Step 1: Extracting audio...")
            
            extract_cmd = [
                "ffmpeg", "-i", self.input_file,
                "-vn", "-acodec", "pcm_s16le",
                "-ar", self.sample_rate_combo.currentText(),
                "-y", temp_audio
            ]
            
            result = subprocess.run(extract_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Audio extraction failed: {result.stderr}")
            
            # Step 2: Apply audio effects (same as audio-only mode)
            temp_processed_audio = os.path.join(self.temp_dir, "processed_audio.wav")
            self.progress_label.setText("Step 2: Applying audio effects...")
            
            # Build audio filter chain
            audio_filters = []
            
            # Volume control
            volume = self.volume_slider.value() / 100.0
            if volume != 1.0:
                audio_filters.append(f"volume={volume},pan=stereo|c0=c0|c1=c1")
            
            # High pass filter
            highpass_freq = self.highpass_slider.value()
            if highpass_freq > 0:
                audio_filters.append(f"highpass=f={highpass_freq}")
            
            # Low pass filter
            lowpass_freq = self.lowpass_slider.value()
            if lowpass_freq > 0:
                audio_filters.append(f"lowpass=f={lowpass_freq}")
            
            # Reverb effect
            if self.reverb_checkbox.isChecked():
                audio_filters.append("aecho=0.9:0.85:60:0.3")
            
            # Distortion effect
            if self.distortion_checkbox.isChecked():
                audio_filters.append("acrusher=bits=6:level_in=2:level_out=2")
            
            # Apply audio processing
            audio_cmd = ["ffmpeg", "-i", temp_audio]
            if audio_filters:
                audio_cmd.extend(["-af", ",".join(audio_filters)])
            audio_cmd.extend(["-y", temp_processed_audio])
            
            result = subprocess.run(audio_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Audio processing failed: {result.stderr}")
            
            # Step 3: Process video separately (no audio)
            temp_video = os.path.join(self.temp_dir, "processed_video.mp4")
            self.progress_label.setText("Step 3: Processing video...")
            
            # Build video filter chain
            video_filters = []
            
            # Scale
            scale = self.resolution_slider.value() / 100.0
            video_filters.append(f"scale=iw*{scale}:ih*{scale}:flags=neighbor")
            
            # Blur
            blur_amount = self.blur_slider.value() / 10.0
            if blur_amount > 0:
                video_filters.append(f"gblur=sigma={blur_amount}")
            
            # Frame rate
            frame_rate = self.framerate_input.value()
            video_filters.append(f"fps={frame_rate}")
            
            # Hue shift
            hue_shift = self.hue_slider.value()
            if hue_shift != 0:
                video_filters.append(f"hue=h={hue_shift}")
            
            # Saturation (will be combined with VHS effects if needed)
            saturation = self.saturation_slider.value() / 100.0
            
            # Media effects
            if self.vhs_checkbox.isChecked():
                # Combine saturation with VHS effects
                vhs_saturation = saturation * 0.8  # VHS effect reduces saturation to 80%
                video_filters.extend([
                    "noise=alls=10:allf=t",
                    f"eq=contrast=1.1:brightness=0.05:saturation={vhs_saturation}",
                    "format=yuv420p,curves=master='0/0 0.2/0.1 0.4/0.3 0.6/0.7 0.8/0.9 1/1'"
                ])
            elif saturation != 1.0:
                # Apply saturation only if VHS is not enabled
                video_filters.append(f"eq=saturation={saturation}")
            
            # Process video
            video_cmd = ["ffmpeg", "-i", self.input_file, "-an"]
            if video_filters:
                video_cmd.extend(["-vf", ",".join(video_filters)])
            video_cmd.extend([
                "-c:v", "libx264",
                "-preset", "fast",
                "-crf", str(self.compression_slider.value()),
                "-r", str(frame_rate),
                "-y", temp_video
            ])
            
            result = subprocess.run(video_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Video processing failed: {result.stderr}")
            
            # Step 4: Merge processed audio back into video
            self.progress_label.setText("Step 4: Merging audio and video...")
            
            merge_cmd = [
                "ffmpeg", "-i", temp_video, "-i", temp_processed_audio,
                "-c:v", "copy",
                "-c:a", "aac",
                "-b:a", self.audio_bitrate_combo.currentText(),
                "-map", "0:v:0",
                "-map", "1:a:0",
                "-shortest",
                "-y", self.output_file
            ]
            
            result = subprocess.run(merge_cmd, capture_output=True, text=True)
            if result.returncode != 0:
                raise Exception(f"Merging failed: {result.stderr}")
            
            self.progress_label.setText("Enhanced processing complete!")
            self.processing_finished(True, "")
            
        except Exception as e:
            self.processing_finished(False, str(e))
    
    def processing_finished_final(self, success, error_msg, original_reverb, original_distortion):
        """Final processing completion - restore settings"""
        # ... (rest of the code remains the same)
        self.reverb_checkbox.setChecked(original_reverb)
        self.distortion_checkbox.setChecked(original_distortion)
        
        self.processing_finished(success, error_msg)
    
    def update_progress(self, message):
        """Update progress bar and label"""
        self.progress_label.setText(message)
        
        # Extract percentage from message
        if "%" in message:
            try:
                import re
                match = re.search(r'(\d+)%', message)
                if match:
                    percentage = int(match.group(1))
                    self.progress_bar.setValue(percentage)
            except:
                pass
        
    def processing_finished(self, success, error_msg):
        """Handle processing completion"""
        self.process_btn.setEnabled(True)
        self.progress_bar.setRange(0, 100)
        
        # Check if output file was actually created
        file_created = success and os.path.exists(self.output_file) and os.path.getsize(self.output_file) > 0
        
        if file_created:
            self.progress_label.setText("Processing complete!")
            self.progress_bar.setValue(100)
            
            # Get file size for user info
            file_size = os.path.getsize(self.output_file)
            file_size_mb = file_size / (1024 * 1024)
            
            reply = QMessageBox.question(
                self, "Success", 
                f"Video processed successfully!\nSaved to: {self.output_file}\nSize: {file_size_mb:.1f} MB\n\nOpen output file?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                import subprocess
                if sys.platform == "win32":
                    os.startfile(self.output_file)
                elif sys.platform == "darwin":
                    subprocess.run(["open", self.output_file])
                else:
                    subprocess.run(["xdg-open", self.output_file])
        else:
            self.progress_label.setText("Processing failed!")
            self.progress_bar.setValue(0)
            
            if not os.path.exists(self.output_file):
                error_msg = f"Output file was not created.\n{error_msg}"
            elif os.path.getsize(self.output_file) == 0:
                error_msg = f"Output file is empty (0 bytes).\n{error_msg}"
            
            QMessageBox.critical(self, "Error", f"Processing failed: {error_msg}")
            
    def extract_frame(self, video_path, output_path, timestamp="00:00:01"):
        """Extract a single frame from video"""
        try:
            cmd = [
                "ffmpeg", "-i", video_path,
                "-ss", timestamp,
                "-vframes", "1",
                "-q:v", "2",
                "-y",
                output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
    
    def extract_frame_at_time(self, input_path, output_path, time_point):
        """Extract a single frame at specific time point"""
        try:
            cmd = [
                "ffmpeg", "-ss", time_point, "-i", input_path,
                "-vframes", "1", "-q:v", "2", "-y", output_path
            ]
            subprocess.run(cmd, check=True, capture_output=True)
            return True
        except subprocess.CalledProcessError:
            return False
            
    def show_original_preview(self):
        """Show multiple original video frames in original preview"""
        if not self.input_file:
            return
        
        # Extract frames at different time points (1, 3, 5, 7 seconds)
        time_points = ["00:00:01", "00:00:03", "00:00:05", "00:00:07"]
        
        for i, time_point in enumerate(time_points):
            temp_frame = os.path.join(self.temp_dir, f"original_frame_{i}.jpg")
            if self.extract_frame_at_time(self.input_file, temp_frame, time_point):
                self.display_preview_image(temp_frame, "original", frame_index=i)
            
    def show_effects_preview(self):
        """Show effects preview with multiple frames in processed preview widget"""
        if not self.input_file:
            return
        
        # Generate frames at different time points (1, 3, 5, 7 seconds)
        time_points = ["00:00:01", "00:00:03", "00:00:05", "00:00:07"]
        
        for i, time_point in enumerate(time_points):
            temp_frame = os.path.join(self.temp_dir, f"effects_frame_{i}.jpg")
            
            # Build optimized frame-only command for this time point
            cmd = self.build_preview_frame_command_at_time(temp_frame, time_point)
            if cmd:
                try:
                    subprocess.run(cmd, check=True, capture_output=True)
                    self.display_preview_image(temp_frame, "processed", frame_index=i)
                except subprocess.CalledProcessError:
                    pass
    
    def build_preview_frame_command(self):
        """Build optimized command for single frame preview (video only)"""
        if not self.input_file:
            return None
            
        temp_frame = os.path.join(self.temp_dir, "effects_frame.jpg")
        cmd = ["ffmpeg", "-i", self.input_file]
        
        # Video filters only (no audio)
        video_filters = []
        
        # Scale
        scale = self.resolution_slider.value() / 100.0
        video_filters.append(f"scale=iw*{scale}:ih*{scale}:flags=neighbor")
        
        # Blur
        blur_amount = self.blur_slider.value() / 10.0
        if blur_amount > 0:
            video_filters.append(f"gblur=sigma={blur_amount}")
        
        # Frame rate
        frame_rate = self.framerate_input.value()
        video_filters.append(f"fps={frame_rate}")
        
        # Hue shift
        hue_shift = self.hue_slider.value()
        if hue_shift != 0:
            video_filters.append(f"hue=h={hue_shift}")
        
        # Saturation (will be combined with VHS effects if needed)
        saturation = self.saturation_slider.value() / 100.0
        
        # Media effects
        if self.vhs_checkbox.isChecked():
            # Combine saturation with VHS effects
            vhs_saturation = saturation * 0.8  # VHS effect reduces saturation to 80%
            video_filters.extend([
                f"eq=brightness=0.05:contrast=1.2:saturation={vhs_saturation}",
                "curves=all='0/0 0.2/0.1 0.5/0.6 1/1'",
                "noise=alls=10:allf=t+u",
                "format=rgb24,format=yuv420p"
            ])
        elif saturation != 1.0:
            # Apply saturation only if VHS is not enabled
            video_filters.append(f"eq=saturation={saturation}")
        
        # Add video filters
        if video_filters:
            cmd.extend(["-vf", ",".join(video_filters)])
        
        # Frame extraction settings
        cmd.extend([
            "-ss", "00:00:01",  # Seek to 1 second
            "-vframes", "1",    # Extract only 1 frame
            "-q:v", "2",        # High quality
            "-an",              # No audio processing!
            "-y",
            temp_frame
        ])
        
        return cmd
    
    def build_preview_frame_command_at_time(self, output_path, time_point):
        """Build optimized command for single frame preview at specific time"""
        if not self.input_file:
            return None
            
        cmd = ["ffmpeg", "-ss", time_point, "-i", self.input_file]
        
        # Video filters only (no audio)
        video_filters = []
        
        # Scale
        scale = self.resolution_slider.value() / 100.0
        video_filters.append(f"scale=iw*{scale}:ih*{scale}:flags=neighbor")
        
        # Blur
        blur_amount = self.blur_slider.value() / 10.0
        if blur_amount > 0:
            video_filters.append(f"gblur=sigma={blur_amount}")
        
        # Frame rate
        frame_rate = self.framerate_input.value()
        video_filters.append(f"fps={frame_rate}")
        
        # Hue shift
        hue_shift = self.hue_slider.value()
        if hue_shift != 0:
            video_filters.append(f"hue=h={hue_shift}")
        
        # Saturation (will be combined with VHS effects if needed)
        saturation = self.saturation_slider.value() / 100.0
        
        # Media effects
        if self.vhs_checkbox.isChecked():
            # Combine saturation with VHS effects
            vhs_saturation = saturation * 0.8  # VHS effect reduces saturation to 80%
            video_filters.extend([
                f"eq=brightness=0.05:contrast=1.2:saturation={vhs_saturation}",
                "curves=all='0/0 0.2/0.1 0.5/0.6 1/1'",
                "noise=alls=10:allf=t+u",
                "format=rgb24,format=yuv420p"
            ])
        elif saturation != 1.0:
            # Apply saturation only if VHS is not enabled
            video_filters.append(f"eq=saturation={saturation}")
        
        # Add video filters
        if video_filters:
            cmd.extend(["-vf", ",".join(video_filters)])
        
        # Frame extraction settings
        cmd.extend([
            "-vframes", "1",    # Extract only 1 frame
            "-q:v", "2",        # High quality
            "-an",              # No audio processing!
            "-y",
            output_path
        ])
        
        return cmd
                        
    def display_preview_image(self, image_path, widget_type="processed", frame_index=0):
        """Display image in specified preview widget frame"""
        try:
            pixmap = QPixmap(image_path)
            if pixmap.isNull():
                # Handle null pixmap (file doesn't exist or can't be loaded)
                if widget_type == "original":
                    if frame_index < len(self.original_preview_widget.preview_frames):
                        self.original_preview_widget.preview_frames[frame_index].setText("Frame Failed")
                else:
                    if frame_index < len(self.processed_preview_widget.preview_frames):
                        self.processed_preview_widget.preview_frames[frame_index].setText("Frame Failed")
                return
                
            # Scale pixmap to fit the smaller frame size
            scaled_pixmap = pixmap.scaled(
                190, 107,  # Match the frame size
                Qt.AspectRatioMode.KeepAspectRatio, 
                Qt.TransformationMode.SmoothTransformation
            )
            
            # Display in the appropriate frame
            if widget_type == "original":
                if frame_index < len(self.original_preview_widget.preview_frames):
                    self.original_preview_widget.preview_frames[frame_index].setPixmap(scaled_pixmap)
            else:
                if frame_index < len(self.processed_preview_widget.preview_frames):
                    self.processed_preview_widget.preview_frames[frame_index].setPixmap(scaled_pixmap)
        except:
            if widget_type == "original":
                if frame_index < len(self.original_preview_widget.preview_frames):
                    self.original_preview_widget.preview_frames[frame_index].setText("Frame Error")
            else:
                if frame_index < len(self.processed_preview_widget.preview_frames):
                    self.processed_preview_widget.preview_frames[frame_index].setText("Frame Error")
            
                
    def closeEvent(self, event):
        """Clean up temp files on close"""
        try:
            if os.path.exists(self.temp_dir):
                shutil.rmtree(self.temp_dir)
        except:
            pass
        event.accept()


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Modern look
    
    window = FFMPEGMediaAnnihilatorGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
