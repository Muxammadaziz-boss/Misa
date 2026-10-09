# ========== tts_manager.py ==========
# TTS boshqaruvchi — Silero TTS (primary) + Edge TTS (fallback)
# Silero: local, tez, o'zbek tili, internet kerak emas
# Edge TTS: internet kerak, lekin bepul va barqaror

import os
import logging
import tempfile
import uuid
import threading
import re

logger = logging.getLogger(__name__)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class TTSManager:
    """Ovoz sintezi boshqaruvchisi.
    
    Ustunlik tartibi:
    1. Silero TTS (local, tez, offline) 
    2. Edge TTS (internet, fallback)
    """
    
    def __init__(self, ovoz_turi: str = "ayol"):
        """
        Args:
            ovoz_turi: "ayol" yoki "erkak"
        """
        self.ovoz_turi = ovoz_turi
        self._silero_model = None
        self._silero_ready = False
        self._lock = threading.Lock()
    
    def preload(self):
        """Modelni background thread da oldindan yuklash (GUI muzlamasligi).
        Dastur boshlaganda chaqirish kerak.
        """
        def _worker():
            logger.info("Silero TTS model yuklanmoqda (background)...")
            self._init_silero()
        
        thread = threading.Thread(target=_worker, daemon=True, name="SileroPreload")
        thread.start()
        
        # Eski temp TTS fayllarni tozalash (oldingi sessiyadan qolgan)
        import glob
        for pattern in ["silero_tts_*.wav", "edge_tts_*.mp3"]:
            for f in glob.glob(os.path.join(tempfile.gettempdir(), pattern)):
                try:
                    os.remove(f)
                except Exception:
                    pass
    
    def _init_silero(self) -> bool:
        """Silero TTS modelini yuklash (bir marta)"""
        if self._silero_ready:
            return True
        
        with self._lock:
            if self._silero_ready:
                return True
            
            try:
                import torch
                
                # Silero TTS model (v4_uz — o'zbek tili, 48kHz)
                model, _ = torch.hub.load(
                    repo_or_dir='snakers4/silero-models',
                    model='silero_tts',
                    language='uz',
                    speaker='v4_uz',
                    trust_repo=True
                )
                
                self._silero_model = model
                self._silero_ready = True
                logger.info("Silero TTS (uz, v4_uz) yuklandi!")
                return True
                
            except Exception as e:
                logger.warning(f"Silero TTS yuklanmadi: {e}")
                return False
    
    def speak_silero(self, text: str, rate: float = 1.0) -> str:
        """Silero TTS bilan ovoz yaratish.
        
        Args:
            text: Gapiriladigan matn
            rate: Tezlik koeffitsienti (0.5 - 2.0)
        
        Returns:
            Audio fayl yo'li (wav) yoki bo'sh string
        """
        if not self._init_silero():
            return ""
        
        try:
            import torch
            
            # Speaker tanlash (Silero uz modelda ko'p speaker'lar)
            # v4_uz modelda speaker'lar: dilnavoz va boshqalar
            speaker = 'dilnavoz'
            
            # Ovoz yaratish
            output_file = os.path.join(
                tempfile.gettempdir(),
                f"silero_tts_{uuid.uuid4()}.wav"
            )
            
            # Matnni tozalash
            text = self._clean_text(text)
            if not text:
                return ""
            
            # Sample rate: 48000Hz (eng yuqori sifat)
            sample_rate = 48000
            
            audio = self._silero_model.apply_tts(
                text=text,
                speaker=speaker,
                sample_rate=sample_rate
            )
            
            # WAV faylga saqlash (torchaudio o'rniga wave moduli)
            import wave
            import numpy as np
            
            # Tensor → numpy → int16
            audio_np = audio.numpy()
            audio_int16 = (audio_np * 32767).astype(np.int16)
            
            with wave.open(output_file, 'wb') as wf:
                wf.setnchannels(1)       # Mono
                wf.setsampwidth(2)       # 16-bit
                wf.setframerate(sample_rate)
                wf.writeframes(audio_int16.tobytes())
            
            logger.debug(f"Silero TTS yaratildi: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Silero TTS xatolik: {e}")
            return ""
    
    async def speak_edge(self, text: str, rate: str = "+0%", 
                          pitch: str = "+0Hz", volume: str = "+0%") -> str:
        """Edge TTS bilan ovoz yaratish (fallback).
        
        Returns:
            Audio fayl yo'li (mp3) yoki bo'sh string
        """
        try:
            import edge_tts
            
            voice = "uz-UZ-MadinaNeural" if self.ovoz_turi == "ayol" else "uz-UZ-SardorNeural"
            
            output_file = os.path.join(
                tempfile.gettempdir(),
                f"edge_tts_{uuid.uuid4()}.mp3"
            )
            
            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch, volume=volume)
            await communicate.save(output_file)
            
            logger.debug(f"Edge TTS yaratildi: {output_file}")
            return output_file
            
        except Exception as e:
            logger.error(f"Edge TTS xatolik: {e}")
            return ""
    
    def speak(self, text: str, kayfiyat_params: dict = None) -> str:
        """Ovoz yaratish — Silero birinchi, Edge TTS fallback.
        
        Args:
            text: Matn
            kayfiyat_params: {"rate": "+0%", "pitch": "+0Hz", "volume": "+0%"}
        
        Returns:
            Audio fayl yo'li
        """
        # 1. Edge TTS (Primary - Madina/Sardor voices)
        import asyncio
        
        params = kayfiyat_params or {}
        rate = params.get("rate", "+0%")
        pitch = params.get("pitch", "+0Hz")
        volume = params.get("volume", "+0%")
        
        try:
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                
            if loop.is_running():
                # Cannot use asyncio.run if loop is running. But typically TTS runs in a separate thread.
                # Let's use run_until_complete if possible.
                pass # will handle below
                
            audio_file = None
            try:
                audio_file = asyncio.run(
                    self.speak_edge(text, rate, pitch, volume)
                )
            except RuntimeError:
                # Event loop is already running
                loop = asyncio.new_event_loop()
                audio_file = loop.run_until_complete(
                    self.speak_edge(text, rate, pitch, volume)
                )
            
            if audio_file:
                return audio_file
        except Exception as e:
            logger.warning(f"Edge TTS xatolik (fallback to Silero): {e}")

        # 2. Silero TTS (Fallback, local, fast, but only female 'dilnavoz' available)
        audio_file = self.speak_silero(text)
        if audio_file:
            return audio_file
        return ""
    
    def play_audio(self, audio_file: str):
        """Audio faylni ijro etish va keyin o'chirish"""
        if not audio_file or not os.path.exists(audio_file):
            return
        
        try:
            import pygame
            
            # Bir marta initsializatsiya (qayta-qayta init qilmaslik)
            if not pygame.mixer.get_init():
                pygame.mixer.init()
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()
            
            # Tugashini kutish
            while pygame.mixer.music.get_busy():
                import time
                time.sleep(0.1)
            
            pygame.mixer.music.unload()
            
        except Exception as e:
            logger.error(f"Audio play xatolik: {e}")
        finally:
            # Vaqtinchalik faylni o'chirish
            try:
                os.remove(audio_file)
            except Exception:
                pass
    
    def speak_and_play(self, text: str, kayfiyat_params: dict = None):
        """Ovoz yaratish va ijro etish — to'liq pipeline"""
        audio_file = self.speak(text, kayfiyat_params)
        if audio_file:
            self.play_audio(audio_file)
    
    def _clean_text(self, text: str) -> str:
        """Matnni TTS uchun tozalash"""
        if not text:
            return ""
        
        # Barcha emoji va maxsus belgilarni olib tashlash
        emoji_pattern = re.compile(
            "["
            "\U0001F300-\U0001F9FF"  # Barcha emoji diapazonlari
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+", flags=re.UNICODE
        )
        text = emoji_pattern.sub('', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        # Juda uzun matnni qisqartirish
        if len(text) > 500:
            text = text[:500] + "..."
        
        return text
    
    @property
    def engine_name(self) -> str:
        """Hozirgi TTS engine nomi"""
        if self._silero_ready:
            return "Silero TTS (local)"
        return "Edge TTS (internet)"


# Global singleton
_tts_manager = None

def get_tts_manager(ovoz_turi: str = "ayol") -> TTSManager:
    """Global TTS manager olish"""
    global _tts_manager
    if _tts_manager is None:
        _tts_manager = TTSManager(ovoz_turi)
    elif _tts_manager.ovoz_turi != ovoz_turi:
        _tts_manager.ovoz_turi = ovoz_turi  # Ovoz turi o'zgarga yangilash
    return _tts_manager
