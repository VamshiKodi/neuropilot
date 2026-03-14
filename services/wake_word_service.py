"""
WakeWordService - Wake word detection using SpeechRecognition or Vosk.

Provides continuous listening for a wake phrase (e.g., "Hey Neuro") and
triggers callbacks when detected. Runs in a background thread without
blocking the main application.
"""

from __future__ import annotations

import os
import threading
import time
from typing import Any, Callable, Dict, List, Optional


class WakeWordService:
    """
    Wake word detection service for hands-free activation.
    
    Listens continuously for a configured wake phrase and triggers callbacks
    when detected. Supports both online (SpeechRecognition) and offline (Vosk)
    recognition backends.
    
    Example:
        wake = WakeWordService(wake_phrases=["hey neuro", "neuropilot", "neuro"])
        wake.on_wake_word = lambda: print("Wake word detected!")
        wake.start_listening()
        # ... later
        wake.stop_listening()
    """

    def __init__(
        self,
        wake_phrases: List[str] | None = None,
        backend: str = "auto",  # "auto", "speech_recognition", "vosk"
        device_index: int | None = None,
        energy_threshold: int = 300,
        pause_threshold: float = 0.8,
        phrase_threshold: float = 0.3,
        timeout: float | None = None,
    ) -> None:
        """
        Initialize wake word service.
        
        Args:
            wake_phrases: List of phrases to detect (case-insensitive).
                          Default: ["hey neuro", "neuropilot", "neuro", "wake up"]
            backend: Recognition backend - "auto", "speech_recognition", or "vosk"
            device_index: Microphone device index (None for default)
            energy_threshold: Energy threshold for speech detection
            pause_threshold: Seconds of silence before phrase ends
            phrase_threshold: Minimum seconds of speaking before considered a phrase
            timeout: Max seconds to listen for audio (None = no timeout)
        """
        self._wake_phrases = wake_phrases or [
            "hey neuro",
            "neuropilot", 
            "neuro",
            "wake up neuro",
            "okay neuro"
        ]
        self._wake_phrases_lower = [p.lower().strip() for p in self._wake_phrases]
        self._backend = backend
        self._device_index = device_index
        self._energy_threshold = energy_threshold
        self._pause_threshold = pause_threshold
        self._phrase_threshold = phrase_threshold
        self._timeout = timeout
        
        # State
        self._listening = False
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._initialized = False
        self._available = False
        self._backend_name: str | None = None
        
        # Callbacks
        self.on_wake_word: Callable[[str], None] | None = None  # Called with detected phrase
        self.on_error: Callable[[str], None] | None = None
        self.on_listening_state_change: Callable[[bool], None] | None = None
        
        # Recognition objects (initialized on start)
        self._recognizer: Any = None
        self._microphone: Any = None
        self._vosk_model: Any = None
        self._vosk_recognizer: Any = None
        
        # Stats
        self._detections: List[Dict[str, Any]] = []
        self._total_listens = 0
        
        # Try to detect what's available
        self._detect_backend()
    
    def _detect_backend(self) -> None:
        """Detect available recognition backend."""
        if self._backend == "speech_recognition":
            self._available = self._check_speech_recognition()
            self._backend_name = "speech_recognition" if self._available else None
        elif self._backend == "vosk":
            self._available = self._check_vosk()
            self._backend_name = "vosk" if self._available else None
        else:  # auto
            if self._check_speech_recognition():
                self._available = True
                self._backend_name = "speech_recognition"
            elif self._check_vosk():
                self._available = True
                self._backend_name = "vosk"
            else:
                self._available = False
                self._backend_name = None
    
    def _check_speech_recognition(self) -> bool:
        """Check if SpeechRecognition is available."""
        try:
            import speech_recognition as sr  # noqa: F401
            return True
        except ImportError:
            return False
    
    def _check_vosk(self) -> bool:
        """Check if Vosk is available."""
        try:
            import vosk  # noqa: F401
            return True
        except ImportError:
            return False
    
    def is_available(self) -> bool:
        """Check if wake word detection is available."""
        return self._available
    
    def get_backend_name(self) -> str | None:
        """Get the detected backend name."""
        return self._backend_name
    
    def _init_speech_recognition(self) -> bool:
        """Initialize SpeechRecognition backend."""
        try:
            import speech_recognition as sr
            
            self._recognizer = sr.Recognizer()
            self._recognizer.energy_threshold = self._energy_threshold
            self._recognizer.pause_threshold = self._pause_threshold
            self._recognizer.phrase_threshold = self._phrase_threshold
            
            # Test microphone access
            self._microphone = sr.Microphone(device_index=self._device_index)
            with self._microphone as source:
                self._recognizer.adjust_for_ambient_noise(source, duration=0.5)
            
            return True
        except Exception as e:
            if self.on_error:
                self.on_error(f"Failed to init SpeechRecognition: {e}")
            return False
    
    def _init_vosk(self) -> bool:
        """Initialize Vosk offline recognition backend."""
        try:
            import vosk
            import pyaudio
            
            # Try to load model from common locations
            model_paths = [
                os.getenv("VOSK_MODEL_PATH"),
                "models/vosk-model-small-en-us-0.15",
                "vosk-model-small-en-us-0.15",
                os.path.expanduser("~/.local/share/vosk/models/vosk-model-small-en-us-0.15"),
                os.path.expanduser("~/vosk-model-small-en-us-0.15"),
            ]
            
            model = None
            for path in model_paths:
                if path and os.path.exists(path):
                    try:
                        model = vosk.Model(path)
                        break
                    except Exception:
                        continue
            
            if model is None:
                # Try to download small model if not found
                if self.on_error:
                    self.on_error("Vosk model not found. Download from https://alphacephei.com/vosk/models")
                return False
            
            self._vosk_model = model
            self._vosk_recognizer = vosk.KaldiRecognizer(model, 16000)
            
            # Init PyAudio
            self._pyaudio = pyaudio.PyAudio()
            self._audio_stream = self._pyaudio.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=16000,
                input=True,
                frames_per_buffer=8000,
                input_device_index=self._device_index,
            )
            
            return True
        except Exception as e:
            if self.on_error:
                self.on_error(f"Failed to init Vosk: {e}")
            return False
    
    def _listen_speech_recognition(self) -> str | None:
        """Listen for audio using SpeechRecognition and return transcript."""
        if not self._recognizer or not self._microphone:
            return None
        
        try:
            import speech_recognition as sr
            
            with self._microphone as source:
                audio = self._recognizer.listen(source, timeout=self._timeout, phrase_time_limit=5)
            
            # Use Google's speech recognition (online)
            text = self._recognizer.recognize_google(audio)
            return text.lower().strip()
        except sr.WaitTimeoutError:
            return None
        except sr.UnknownValueError:
            return None
        except sr.RequestError:
            # API unavailable
            return None
        except Exception:
            return None
    
    def _listen_vosk(self) -> str | None:
        """Listen for audio using Vosk offline recognition."""
        if not self._vosk_recognizer or not hasattr(self, '_audio_stream'):
            return None
        
        try:
            import json
            
            self._vosk_recognizer.Reset()
            
            # Listen for up to 5 seconds of audio
            start_time = time.time()
            while not self._stop_event.is_set():
                if time.time() - start_time > 5:
                    break
                    
                data = self._audio_stream.read(4000, exception_on_overflow=False)
                if self._vosk_recognizer.AcceptWaveform(data):
                    result = json.loads(self._vosk_recognizer.Result())
                    text = result.get("text", "").strip().lower()
                    if text:
                        return text
            
            # Check final result
            result = json.loads(self._vosk_recognizer.FinalResult())
            text = result.get("text", "").strip().lower()
            return text if text else None
            
        except Exception:
            return None
    
    def _check_wake_phrase(self, text: str) -> str | None:
        """Check if text contains any wake phrase. Returns the matched phrase."""
        if not text:
            return None
        
        text_lower = text.lower().strip()
        
        for phrase in self._wake_phrases_lower:
            if phrase in text_lower:
                return phrase
        
        return None
    
    def _listening_loop(self) -> None:
        """Main listening loop that runs in background thread."""
        if self.on_listening_state_change:
            self.on_listening_state_change(True)
        
        while not self._stop_event.is_set():
            try:
                self._total_listens += 1
                
                # Listen for audio
                if self._backend_name == "speech_recognition":
                    text = self._listen_speech_recognition()
                elif self._backend_name == "vosk":
                    text = self._listen_vosk()
                else:
                    break
                
                # Check for wake phrase
                detected = self._check_wake_phrase(text) if text else None
                
                if detected:
                    detection = {
                        "timestamp": time.time(),
                        "phrase": detected,
                        "full_text": text,
                        "backend": self._backend_name,
                    }
                    self._detections.append(detection)
                    
                    # Keep only last 100 detections
                    if len(self._detections) > 100:
                        self._detections = self._detections[-100:]
                    
                    # Trigger callback
                    if self.on_wake_word:
                        try:
                            self.on_wake_word(detected)
                        except Exception:
                            pass
                
                # Small delay to prevent CPU spinning
                time.sleep(0.1)
                
            except Exception as e:
                if self.on_error:
                    try:
                        self.on_error(str(e))
                    except Exception:
                        pass
                time.sleep(1)  # Back off on error
        
        if self.on_listening_state_change:
            self.on_listening_state_change(False)
    
    def start_listening(self) -> Dict[str, Any]:
        """
        Start listening for wake word in background thread.
        
        Returns:
            Dict with success status and message
        """
        if not self._available:
            return {"ok": False, "error": "No speech recognition backend available. Install SpeechRecognition or Vosk."}
        
        if self._listening:
            return {"ok": False, "error": "Already listening"}
        
        # Initialize backend
        if self._backend_name == "speech_recognition":
            if not self._init_speech_recognition():
                return {"ok": False, "error": "Failed to initialize SpeechRecognition"}
        elif self._backend_name == "vosk":
            if not self._init_vosk():
                return {"ok": False, "error": "Failed to initialize Vosk"}
        
        # Start listening thread
        self._stop_event.clear()
        self._listening = True
        self._thread = threading.Thread(target=self._listening_loop, daemon=True)
        self._thread.start()
        
        return {"ok": True, "backend": self._backend_name, "wake_phrases": self._wake_phrases}
    
    def stop_listening(self) -> Dict[str, Any]:
        """
        Stop listening for wake word.
        
        Returns:
            Dict with success status
        """
        if not self._listening:
            return {"ok": False, "error": "Not currently listening"}
        
        self._stop_event.set()
        self._listening = False
        
        # Wait for thread to finish (with timeout)
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)
        
        # Cleanup resources
        self._cleanup()
        
        return {"ok": True}
    
    def _cleanup(self) -> None:
        """Clean up resources."""
        try:
            if hasattr(self, '_audio_stream') and self._audio_stream:
                self._audio_stream.stop_stream()
                self._audio_stream.close()
                self._audio_stream = None
        except Exception:
            pass
        
        try:
            if hasattr(self, '_pyaudio') and self._pyaudio:
                self._pyaudio.terminate()
                self._pyaudio = None
        except Exception:
            pass
        
        self._recognizer = None
        self._microphone = None
        self._vosk_model = None
        self._vosk_recognizer = None
    
    def is_listening(self) -> bool:
        """Check if currently listening."""
        return self._listening and self._thread is not None and self._thread.is_alive()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status and stats."""
        return {
            "available": self._available,
            "backend": self._backend_name,
            "listening": self.is_listening(),
            "wake_phrases": self._wake_phrases,
            "total_listens": self._total_listens,
            "detections": len(self._detections),
            "recent_detections": self._detections[-10:] if self._detections else [],
        }
    
    def get_detections(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get detection history."""
        return self._detections[-limit:]
    
    def clear_detections(self) -> None:
        """Clear detection history."""
        self._detections.clear()
    
    def update_wake_phrases(self, phrases: List[str]) -> None:
        """Update the list of wake phrases."""
        self._wake_phrases = phrases
        self._wake_phrases_lower = [p.lower().strip() for p in phrases]
