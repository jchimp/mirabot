"""
ChatService — orchestrates the STT → LLM → TTS pipeline.
Now with optional calendar context injection.
"""
import base64
import struct
import logging

from providers.base import STTProvider, TTSProvider, LLMProvider

log = logging.getLogger(__name__)


class ChatService:
    def __init__(self, stt: STTProvider, tts: TTSProvider, llm: LLMProvider,
                 system_prompt: str = "", calendar_context=None):
        self.stt = stt
        self.tts = tts
        self.llm = llm
        self.system_prompt = system_prompt
        self.calendar_context = calendar_context   # CalendarContext or None

    def converse(self, audio_bytes: bytes, context: list[dict],
                 mime_type: str = "audio/webm") -> dict:
        """
        Full pipeline: audio → text → LLM → speech.
        """
        # Speech-to-Text
        log.info("STT: transcribing %d bytes (%s)", len(audio_bytes), mime_type)
        user_text = self.stt.transcribe(audio_bytes, mime_type)
        log.info("STT result: %s", user_text)

        if not user_text:
            return {
                "user_text": "",
                "response_text": "I didn't catch that — could you try again?",
                "audio_b64": self._silent_audio_b64(),
            }

        # Build message list
        messages = []

        # System prompt + calendar context
        system = self.system_prompt
        if self.calendar_context and self.calendar_context.enabled:
            try:
                cal_ctx = self.calendar_context.get_context_string()
                if cal_ctx:
                    system = system.rstrip() + "\n" + cal_ctx
                    log.info("Calendar context injected (%d chars)", len(cal_ctx))
            except Exception as e:
                log.warning("Calendar context failed: %s", e)

        if system:
            messages.append({"role": "system", "content": system})

        # Append user message to the prompts and context
        messages.extend(context)
        messages.append({"role": "user", "content": user_text})

        # LLM chat
        log.info("LLM: sending %d messages", len(messages))
        response_text = self.llm.chat(messages)
        log.info("LLM result: %s", response_text[:120])

        # Text-to-Speech
        log.info("TTS: synthesizing %d chars", len(response_text))
        wav_bytes = self.tts.synthesize(response_text)
        audio_b64 = base64.b64encode(wav_bytes).decode("ascii")

        return {
            "user_text": user_text,
            "response_text": response_text,
            "audio_b64": audio_b64,
        }

    @staticmethod
    def _silent_audio_b64() -> str:
        sr, dur = 22050, 0.1
        n = int(sr * dur)
        data_size = n * 2
        # 0.1s of silence at 22050 Hz, 16-bit mono
        header = struct.pack(
            "<4sI4s4sIHHIIHH4sI",
            b"RIFF", 36 + data_size, b"WAVE",
            b"fmt ", 16, 1, 1, sr, sr * 2, 2, 16,
            b"data", data_size,
        )
        return base64.b64encode(header + b"\x00" * data_size).decode("ascii")