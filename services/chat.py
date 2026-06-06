"""
ChatService — orchestrates the STT → LLM → TTS pipeline.
Now with optional calendar context injection and SSE streaming.
"""
import re
import base64
import struct
import logging
from typing import Iterator

from providers.base import STTProvider, TTSProvider, LLMProvider

log = logging.getLogger(__name__)

# Split on sentence-ending punctuation, paragraph breaks, or list-item boundaries.
_SENTENCE_SPLIT = re.compile(r'(?<=[.!?])\s+|\n{2,}|\n(?=\s*[-*\d])')

# Ordered stripping rules: code fences first so inline patterns don't match inside them.
_MD_STRIP = [
    (re.compile(r'```[\s\S]*?```', re.DOTALL), ''),          # fenced code blocks
    (re.compile(r'`(.+?)`'),                    r'\1'),       # inline code
    (re.compile(r'^#{1,6}\s+', re.MULTILINE),   ''),          # headers
    (re.compile(r'\*{3}(.+?)\*{3}', re.DOTALL), r'\1'),       # ***bold italic***
    (re.compile(r'\*{2}(.+?)\*{2}', re.DOTALL), r'\1'),       # **bold**
    (re.compile(r'\*(.+?)\*',       re.DOTALL), r'\1'),       # *italic*
    (re.compile(r'_{3}(.+?)_{3}',   re.DOTALL), r'\1'),       # ___bold italic___
    (re.compile(r'_{2}(.+?)_{2}',   re.DOTALL), r'\1'),       # __bold__
    (re.compile(r'_(.+?)_',         re.DOTALL), r'\1'),       # _italic_
    (re.compile(r'\[(.+?)\]\(.+?\)'),            r'\1'),       # [links](url)
    (re.compile(r'^[-*+]\s+', re.MULTILINE),    ''),          # unordered list markers
    (re.compile(r'^\d+\.\s+', re.MULTILINE),    ''),          # ordered list markers
    (re.compile(r'^>{1,}\s*', re.MULTILINE),    ''),          # blockquotes
    (re.compile(r'^[-*_]{3,}\s*$', re.MULTILINE), '.'),       # horizontal rules → pause
]


def _strip_markdown(text: str) -> str:
    """Remove markdown syntax, leaving plain speakable text for TTS."""
    for pattern, replacement in _MD_STRIP:
        text = pattern.sub(replacement, text)
    text = re.sub(r'\n{2,}', '. ', text)   # paragraph breaks → spoken pause
    text = re.sub(r'\n', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


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

    def converse_stream(self, audio_bytes: bytes, context: list[dict],
                        mime_type: str = "audio/webm") -> Iterator[dict]:
        """
        Streaming pipeline: audio → transcript → LLM tokens → TTS chunks.
        Yields event dicts:
          {"type": "transcript", "text": str}
          {"type": "chunk", "text": str, "audio": base64_str}
          {"type": "done", "user_text": str, "response_text": str}
          {"type": "error", "message": str}
        """
        # STT
        log.info("STT: transcribing %d bytes (%s)", len(audio_bytes), mime_type)
        user_text = self.stt.transcribe(audio_bytes, mime_type)
        log.info("STT result: %s", user_text)
        yield {"type": "transcript", "text": user_text}

        if not user_text:
            yield {
                "type": "chunk",
                "text": "I didn't catch that — could you try again?",
                "audio": self._silent_audio_b64(),
            }
            yield {"type": "done", "user_text": "", "response_text": ""}
            return

        # Build messages
        messages = []
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
        messages.extend(context)
        messages.append({"role": "user", "content": user_text})

        # Stream LLM tokens → accumulate sentences → synthesize each
        log.info("LLM: streaming %d messages", len(messages))
        buf = ""
        full_response = ""

        try:
            for token in self.llm.chat_stream(messages):
                buf += token
                full_response += token

                # Flush any complete sentences from the buffer
                parts = _SENTENCE_SPLIT.split(buf)
                if len(parts) > 1:
                    for sentence in parts[:-1]:
                        sentence = sentence.strip()
                        if not sentence:
                            continue
                        log.info("TTS: synthesizing sentence (%d chars)", len(sentence))
                        wav = self.tts.synthesize(_strip_markdown(sentence))
                        yield {
                            "type": "chunk",
                            "text": sentence,
                            "audio": base64.b64encode(wav).decode("ascii"),
                        }
                    buf = parts[-1]
        except Exception as e:
            log.exception("LLM stream error")
            yield {"type": "error", "message": str(e)}
            return

        # Flush any remaining text
        remainder = buf.strip()
        if remainder:
            log.info("TTS: synthesizing remainder (%d chars)", len(remainder))
            wav = self.tts.synthesize(_strip_markdown(remainder))
            yield {
                "type": "chunk",
                "text": remainder,
                "audio": base64.b64encode(wav).decode("ascii"),
            }

        yield {"type": "done", "user_text": user_text, "response_text": full_response}

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