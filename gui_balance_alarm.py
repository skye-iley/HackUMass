
import sys
import json
import os
import asyncio
import threading
from datetime import datetime, timedelta, timezone, time
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QTimeEdit, QDialog, QMessageBox, QFrame,
    QScrollArea, QGridLayout
)
from PyQt6.QtCore import Qt, QTimer, QTime, pyqtSignal, QThread, QDateTime
from PyQt6.QtGui import QFont, QColor, QIcon, QPixmap
from PyQt6.QtCore import Qt as QtCore
from PyQt6.QtGui import QPalette

# Import backend modules
try:
    from fetch_calendar import auth_fetch
    from gemini import analyze_calendar_data, call_gemini_api
    from speech import text_to_speech_save_file
    from alarm_control import get_gemini_recommendations
    from dotenv import load_dotenv
    load_dotenv()
except Exception as e:
    print(f"Warning: Could not import backend modules: {e}")

# Cross-platform audio support
try:
    import pygame
    PYGAME_AVAILABLE = True
except ImportError:
    PYGAME_AVAILABLE = False
    print("Note: Install pygame for better audio support: pip install pygame")

# ============================================================================
# MATERIAL DESIGN COLORS
# ============================================================================
COLORS = {
    "primary": "#6200EA",      # Deep Purple
    "secondary": "#03DAC6",    # Teal
    "surface": "#FFFFFF",
    "background": "#F5F5F5",
    "error": "#FF5252",         # Alert Red
    "warning": "#FF9100",       # Orange
    "success": "#4CAF50",       # Green
    "text_primary": "#212121",
    "text_secondary": "#757575",
}

TIMEZONE = timezone(timedelta(hours=-5))  # EST
LOCATION = "Amherst, Massachusetts"

# ============================================================================
# STYLED WIDGETS
# ============================================================================

class MaterialCard(QFrame):
    """Material Design Card"""
    def __init__(self, title="", parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {COLORS['surface']};
                border-radius: 8px;
                border: 1px solid #E0E0E0;
            }}
        """)
        self.setLineWidth(0)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)

        if title:
            title_label = QLabel(title)
            title_font = QFont("Segoe UI", 16, QFont.Weight.Bold)
            title_label.setFont(title_font)
            title_label.setStyleSheet(f"color: {COLORS['text_primary']};")
            layout.addWidget(title_label)

        self.content_layout = QVBoxLayout()
        layout.addLayout(self.content_layout)


class MaterialButton(QPushButton):
    """Material Design Button"""
    def __init__(self, text, parent=None, color="primary", size="medium"):
        super().__init__(text, parent)
        self.color = color
        self.size = size

        colors = COLORS[color] if color in COLORS else COLORS["primary"]

        font_size = 14 if size == "large" else 12
        self.setFont(QFont("Segoe UI", font_size))

        padding = "16px 32px" if size == "large" else "8px 16px"
        border_radius = "50px" if size == "large" else "4px"

        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {colors};
                color: white;
                border: none;
                border-radius: {border_radius};
                padding: {padding};
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {self.darken_color(colors, 20)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(colors, 40)};
            }}
        """)

    @staticmethod
    def darken_color(hex_color, percent):
        """Darken a hex color by percent"""
        hex_color = hex_color.lstrip("#")
        rgb = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        darkened = tuple(max(0, int(c * (1 - percent/100))) for c in rgb)
        return f"#{darkened[0]:02x}{darkened[1]:02x}{darkened[2]:02x}"


# ============================================================================
# CROSS-PLATFORM AUDIO GENERATOR
# ============================================================================

class AudioAlarmGenerator:
    """Generate and play alarm tones cross-platform (macOS, Linux, Windows)"""

    def __init__(self):
        self.is_playing = False
        self.use_pygame = PYGAME_AVAILABLE
        self.afplay_process = None

        if self.use_pygame:
            try:
                pygame.mixer.init()
                print("✓ Pygame audio initialized")
            except Exception as e:
                self.use_pygame = False
                print(f"⚠ Pygame initialization failed: {e}")

    def generate_sine_wave(self, frequency=900, duration=0.5, sample_rate=44100):
        """Generate a sine wave using numpy"""
        try:
            import numpy as np
            t = np.linspace(0, duration, int(sample_rate * duration))
            wave = np.sin(2 * np.pi * frequency * t) * 0.7
            return wave
        except ImportError:
            print("⚠ numpy not available, using basic tone generation")
            return None

    def play_alarm_pygame(self):
        """Play alarm using pygame"""
        try:
            import numpy as np
            from scipy.io import wavfile

            # Generate beep + silence pattern
            sample_rate = 44100
            beep_duration = 0.5
            silence_duration = 0.5

            # Create one cycle of beep + silence
            beep = self.generate_sine_wave(900, beep_duration, sample_rate)
            silence = np.zeros(int(silence_duration * sample_rate))

            if beep is None:
                return False

            # Combine
            alarm_cycle = np.concatenate([beep, silence])
            alarm_cycle = (alarm_cycle * 32767).astype(np.int16)

            # Save temporarily
            temp_file = "/tmp/alarm_tone.wav"
            wavfile.write(temp_file, sample_rate, alarm_cycle)

            # Play with pygame
            sound = pygame.mixer.Sound(temp_file)

            # Loop the sound
            self.is_playing = True
            sound.play(-1)  # -1 means loop indefinitely

            return True
        except Exception as e:
            print(f"⚠ Pygame audio error: {e}")
            return False

    def play_alarm_afplay(self):
        """Play alarm using macOS afplay command (no dependencies)"""
        try:
            import subprocess
            import numpy as np
            from scipy.io import wavfile

            # Generate beep + silence pattern
            sample_rate = 44100
            beep_duration = 0.5
            silence_duration = 0.5

            beep = self.generate_sine_wave(900, beep_duration, sample_rate)
            silence = np.zeros(int(silence_duration * sample_rate))

            if beep is None:
                return False

            alarm_cycle = np.concatenate([beep, silence])
            alarm_cycle = (alarm_cycle * 32767).astype(np.int16)

            # Save to temp file
            temp_file = "/tmp/alarm_tone.wav"
            wavfile.write(temp_file, sample_rate, alarm_cycle)

            # Loop using afplay (macOS native)
            self.afplay_process = subprocess.Popen(
                ["afplay", "-l", "0", temp_file],  # -l 0 = infinite loop
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            self.is_playing = True
            return True
        except Exception as e:
            print(f"⚠ afplay error: {e}")
            return False

    def play_alarm_fallback(self):
        """Fallback: Use system beep sound via subprocess"""
        try:
            import subprocess
            import time

            # Play system alert sound multiple times
            for i in range(8):  # Play 4 times (each is 1 second)
                subprocess.run(["afplay", "/System/Library/Sounds/Alarm.aiff"], 
                             timeout=2, check=False)
                time.sleep(0.5)  # Small gap between beeps
            return True
        except Exception as e:
            print(f"⚠ Fallback alarm error: {e}")
            return False

    def play_alarm(self):
        """Play alarm tone with best available method"""
        print("🔔 Starting alarm...")

        # Try pygame first if available
        if self.use_pygame and self.play_alarm_pygame():
            return

        # Try macOS afplay
        try:
            import platform
            if platform.system() == "Darwin":  # macOS
                if self.play_alarm_afplay():
                    return
        except:
            pass

        # Fallback to system sounds
        self.play_alarm_fallback()

    def stop_alarm(self):
        """Stop the alarm"""
        self.is_playing = False

        if self.use_pygame:
            try:
                pygame.mixer.stop()
            except:
                pass

        # Terminate afplay process if running
        try:
            if self.afplay_process:
                self.afplay_process.terminate()
        except:
            pass

        print("🔔 Alarm stopped")


# ============================================================================
# MAIN GUI WINDOW
# ============================================================================

class BalanceAlarmApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Balance Alarm - Smart Sleep & Schedule Manager")
        self.setGeometry(100, 100, 1200, 900)
        self.setStyleSheet(f"background-color: {COLORS['background']};")

        # State variables
        self.alarm_time = QTime(7, 0)  # Default 7:00 AM
        self.alarm_armed = False
        self.alarm_triggered = False
        self.greeting_text = ""
        self.audio_file = "output.mp3"

        # Audio manager
        self.audio_manager = AudioAlarmGenerator()

        # Initialize UI
        self.init_ui()

        # Timer for checking current time and updating UI
        self.timer = QTimer()
        self.timer.timeout.connect(self.check_alarm)
        self.timer.start(500)  # Check every 500ms

    def init_ui(self):
        """Initialize UI components"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(20, 20, 20, 20)
        main_layout.setSpacing(16)

        # ===== HEADER SECTION =====
        header_layout = QHBoxLayout()

        current_time_label = QLabel()
        current_time_label.setFont(QFont("Segoe UI", 48, QFont.Weight.Bold))
        current_time_label.setStyleSheet(f"color: {COLORS['primary']};")
        self.current_time_label = current_time_label

        greeting_label = QLabel("Good Morning")
        greeting_label.setFont(QFont("Segoe UI", 20))
        greeting_label.setStyleSheet(f"color: {COLORS['text_secondary']};")

        header_layout.addWidget(current_time_label)
        header_layout.addStretch()
        header_layout.addWidget(greeting_label)

        main_layout.addLayout(header_layout)

        # ===== ALARM SETTING SECTION =====
        alarm_card = MaterialCard("Set Daily Alarm")

        alarm_controls = QHBoxLayout()

        time_label = QLabel("Alarm Time:")
        time_label.setFont(QFont("Segoe UI", 12))
        alarm_controls.addWidget(time_label)

        time_edit = QTimeEdit()
        time_edit.setTime(self.alarm_time)
        time_edit.setFont(QFont("Segoe UI", 12))
        time_edit.timeChanged.connect(self.on_alarm_time_changed)
        self.time_edit = time_edit
        alarm_controls.addWidget(time_edit)

        arm_button = MaterialButton("Arm Alarm", color="primary")
        arm_button.clicked.connect(self.arm_alarm)
        self.arm_button = arm_button
        alarm_controls.addWidget(arm_button)

        test_button = MaterialButton("Test Alarm", color="secondary")
        test_button.clicked.connect(self.test_alarm)
        alarm_controls.addWidget(test_button)

        alarm_controls.addStretch()

        next_alarm_label = QLabel("Next alarm: 7:00 AM")
        next_alarm_label.setFont(QFont("Segoe UI", 11))
        next_alarm_label.setStyleSheet(f"color: {COLORS['text_secondary']};")
        self.next_alarm_label = next_alarm_label
        alarm_controls.addWidget(next_alarm_label)

        alarm_card.content_layout.addLayout(alarm_controls)
        main_layout.addWidget(alarm_card)

        # ===== STRESS ANALYSIS SECTION =====
        stress_layout = QHBoxLayout()

        past_week_card = MaterialCard("Past Week Analysis")
        past_text = QLabel("Busyness: 97.5%\nHours: 39/40\nStatus: High Stress")
        past_text.setFont(QFont("Segoe UI", 11))
        past_week_card.content_layout.addWidget(past_text)
        stress_layout.addWidget(past_week_card)

        upcoming_week_card = MaterialCard("Upcoming Week Forecast")
        upcoming_text = QLabel("Busyness: 105%\nHours: 42/40\nStatus: Critical")
        upcoming_text.setFont(QFont("Segoe UI", 11))
        upcoming_week_card.content_layout.addWidget(upcoming_text)
        stress_layout.addWidget(upcoming_week_card)

        main_layout.addLayout(stress_layout)

        # ===== TODAY'S SCHEDULE SECTION =====
        schedule_card = MaterialCard("Today's Schedule")

        schedule_text = QLabel(
            "9:00 AM - 9:30 AM: Morning Stand-up\n"
            "11:00 AM - 12:00 PM: Dentist Appointment\n"
            "3:00 PM - 4:30 PM: Project Phoenix Review\n\n"
            "Free slots: 9:30-11:00 AM, 12:00-3:00 PM, 4:30-5:00 PM"
        )
        schedule_text.setFont(QFont("Segoe UI", 10))
        schedule_card.content_layout.addWidget(schedule_text)

        main_layout.addWidget(schedule_card)

        # ===== AUDIO PLAYER SECTION =====
        audio_card = MaterialCard("Morning Briefing")

        play_button = MaterialButton("▶ Play", color="primary", size="large")
        play_button.clicked.connect(self.play_audio)
        audio_card.content_layout.addWidget(play_button)

        main_layout.addWidget(audio_card)

        # Add stretch to push everything to top
        main_layout.addStretch()

        # ===== STATUS BAR =====
        status_label = QLabel("Alarm: Armed | Ready to wake you up")
        status_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        self.status_label = status_label
        main_layout.addWidget(status_label)

        # Update current time display
        self.update_current_time()

    def update_current_time(self):
        """Update the current time display"""
        current = datetime.now().strftime("%H:%M")
        self.current_time_label.setText(current)

    def on_alarm_time_changed(self):
        """Handle alarm time change"""
        self.alarm_time = self.time_edit.time()
        self.update_next_alarm_display()

    def update_next_alarm_display(self):
        """Update the next alarm countdown"""
        now = datetime.now().time()
        alarm_time = self.alarm_time.toPyTime()

        if alarm_time > now:
            delta = datetime.combine(datetime.today(), alarm_time) - datetime.combine(datetime.today(), now)
        else:
            delta = datetime.combine(datetime.today() + timedelta(days=1), alarm_time) - datetime.combine(datetime.today(), now)

        hours, remainder = divmod(int(delta.total_seconds()), 3600)
        minutes = remainder // 60

        self.next_alarm_label.setText(f"Next alarm in {hours}h {minutes}m")

    def arm_alarm(self):
        """Arm the alarm"""
        self.alarm_armed = True
        self.arm_button.setText("Alarm Armed ✓")
        self.arm_button.setEnabled(False)
        self.status_label.setText("Alarm: Armed | Ready to wake you up")
        self.status_label.setStyleSheet(f"color: {COLORS['success']}; font-weight: bold;")
        QMessageBox.information(self, "Alarm Armed", f"Alarm set for {self.alarm_time.toString('h:mm AP')}")

    def test_alarm(self):
        """Test the alarm (trigger immediately)"""
        self.trigger_alarm()

    def check_alarm(self):
        """Check if it's time for the alarm"""
        self.update_current_time()
        self.update_next_alarm_display()

        if not self.alarm_armed or self.alarm_triggered:
            return

        current = datetime.now().time()
        alarm_time = self.alarm_time.toPyTime()

        # Check if current time matches alarm time (within same minute)
        if (current.hour == alarm_time.hour and 
            current.minute == alarm_time.minute):
            self.trigger_alarm()

    def trigger_alarm(self):
        """Trigger the alarm"""
        self.alarm_triggered = True
        self.show_alarm_overlay()

    def show_alarm_overlay(self):
        """Show alarm overlay with ringtone"""
        # Create alarm dialog
        alarm_dialog = QDialog(self)
        alarm_dialog.setWindowTitle("ALARM! Wake Up!")
        alarm_dialog.setGeometry(100, 100, 600, 400)
        alarm_dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {COLORS['error']};
            }}
        """)
        alarm_dialog.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)

        layout = QVBoxLayout(alarm_dialog)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(20)

        # Alarm text
        alarm_text = QLabel("⏰ ALARM ⏰\nIt's time to wake up!")
        alarm_text.setFont(QFont("Segoe UI", 40, QFont.Weight.Bold))
        alarm_text.setStyleSheet("color: white;")
        alarm_text.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(alarm_text)

        layout.addStretch()

        # Acknowledge button
        ack_button = MaterialButton("Acknowledge Alarm", color="success", size="large")
        ack_button.clicked.connect(lambda: self.acknowledge_alarm(alarm_dialog))
        layout.addWidget(ack_button)

        # Play ringtone in background thread
        alarm_thread = threading.Thread(target=self.audio_manager.play_alarm, daemon=True)
        alarm_thread.start()

        alarm_dialog.exec()

    def acknowledge_alarm(self, dialog):
        """Acknowledge the alarm"""
        dialog.close()
        self.audio_manager.stop_alarm()
        self.show_greeting()

    def show_greeting(self):
        """Show personalized greeting"""
        greeting_dialog = QDialog(self)
        greeting_dialog.setWindowTitle("Good Morning!")
        greeting_dialog.setGeometry(150, 150, 700, 500)
        greeting_dialog.setStyleSheet(f"background-color: {COLORS['surface']};")

        layout = QVBoxLayout(greeting_dialog)
        layout.setContentsMargins(30, 30, 30, 30)
        layout.setSpacing(15)

        greeting_label = QLabel("Good morning! Your personalized balance briefing is ready.")
        greeting_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        greeting_label.setStyleSheet(f"color: {COLORS['primary']};")
        layout.addWidget(greeting_label)

        # Schedule preview
        schedule_label = QLabel("Today's Schedule:")
        schedule_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(schedule_label)

        schedule_text = QLabel(
            "• 9:00 AM - Morning Stand-up\n"
            "• 11:00 AM - Dentist Appointment\n"
            "• 3:00 PM - Project Phoenix Review"
        )
        schedule_text.setFont(QFont("Segoe UI", 11))
        layout.addWidget(schedule_text)

        # Recommendations
        rec_label = QLabel("Today's Recommendations:")
        rec_label.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
        layout.addWidget(rec_label)

        rec_text = QLabel(
            "✓ Take a mindful lunch break at noon\n"
            "✓ Consider a 15-min walk mid-afternoon\n"
            "✓ Your afternoon is open for focused work"
        )
        rec_text.setFont(QFont("Segoe UI", 11))
        layout.addWidget(rec_text)

        layout.addStretch()

        # Play and dismiss buttons
        button_layout = QHBoxLayout()

        play_btn = MaterialButton("▶ Play Briefing", color="primary")
        play_btn.clicked.connect(self.play_audio)
        button_layout.addWidget(play_btn)

        dismiss_btn = MaterialButton("Dismiss", color="secondary")
        dismiss_btn.clicked.connect(greeting_dialog.close)
        button_layout.addWidget(dismiss_btn)

        layout.addLayout(button_layout)

        greeting_dialog.exec()

    def play_audio(self):
        """Play the generated audio briefing"""
        print(f"Playing audio: {self.audio_file}")
        try:
            import subprocess
            import platform

            if platform.system() == "Darwin":  # macOS
                subprocess.run(["afplay", self.audio_file], check=False, timeout=30)
            elif platform.system() == "Linux":
                subprocess.run(["paplay", self.audio_file], check=False, timeout=30)
            else:
                QMessageBox.information(self, "Audio Playback", f"Would play: {self.audio_file}")
        except Exception as e:
            QMessageBox.information(self, "Audio Playback", f"Playing generated briefing...\n(Error: {e})")

    def closeEvent(self, event):
        """Handle window close"""
        self.timer.stop()
        self.audio_manager.stop_alarm()
        event.accept()


# ============================================================================
# MAIN APPLICATION
# ============================================================================

def main():
    app = QApplication(sys.argv)
    window = BalanceAlarmApp()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
