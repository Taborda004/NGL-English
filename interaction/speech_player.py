"""
Speech Player module: synthesizes English speech and plays it directly to VB-Audio CABLE Input.
Used for automatically answering Speaking exercises in learn.eltngl.com.
"""
import os
import tempfile
import logging
import sounddevice as sd
import soundfile as sf
import pyttsx3

logger = logging.getLogger(__name__)

class SpeechPlayer:
    def __init__(self):
        self.device_idx = self._find_cable_input_device()
        self._init_tts_engine()

    def _find_cable_input_device(self) -> int | None:
        """Finds the index of 'CABLE Input' device for playback."""
        try:
            devices = sd.query_devices()
            for idx, dev in enumerate(devices):
                if "cable input" in dev["name"].lower() and dev.get("max_output_channels", 0) > 0:
                    return idx
        except Exception as e:
            logger.warning(f"Error querying audio devices: {e}")
        return None

    def _init_tts_engine(self):
        try:
            self.engine = pyttsx3.init()
            voices = self.engine.getProperty('voices')
            # Select an English voice (David or Zira in Windows)
            en_voice = next((v for v in voices if 'en' in v.id.lower() or 'english' in v.name.lower() or 'david' in v.name.lower() or 'zira' in v.name.lower()), voices[0] if voices else None)
            if en_voice:
                self.engine.setProperty('voice', en_voice.id)
            self.engine.setProperty('rate', 145) # Natural English speaking rate
        except Exception as e:
            logger.error(f"Error initializing TTS engine: {e}")
            self.engine = None

    def play_sentence(self, text: str) -> bool:
        """
        Synthesizes the English sentence and streams it directly to CABLE Input.
        Returns True if played successfully, False otherwise.
        """
        if not text or not self.engine:
            return False

        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp_file:
                tmp_path = tmp_file.name

            # Generate WAV
            self.engine.save_to_file(text, tmp_path)
            self.engine.runAndWait()

            if not os.path.exists(tmp_path) or os.path.getsize(tmp_path) == 0:
                return False

            # Play WAV to CABLE Input
            data, samplerate = sf.read(tmp_path)
            target_device = self.device_idx
            
            sd.play(data, samplerate=samplerate, device=target_device)
            sd.wait()
            return True
        except Exception as e:
            logger.error(f"Error playing TTS to cable: {e}")
            return False
        finally:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.remove(tmp_path)
                except Exception:
                    pass
