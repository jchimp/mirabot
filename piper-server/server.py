"""
Thin HTTP wrapper around piper-tts.
Accepts text, returns WAV audio.
Mount voice models at /models.
"""
import io
import os
import wave
import logging

from flask import Flask, request, Response, jsonify
from piper.voice import PiperVoice

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

app = Flask(__name__)

MODEL_DIR = os.environ.get("PIPER_MODEL_DIR", "/models")
DEFAULT_VOICE = os.environ.get("PIPER_DEFAULT_VOICE", "en_US-lessac-medium")

_voices: dict[str, PiperVoice] = {}


def _get_voice(name: str) -> PiperVoice:
    if name not in _voices:
        model_path = os.path.join(MODEL_DIR, f"{name}.onnx")
        config_path = f"{model_path}.json"
        log.info("Loading voice: %s", model_path)
        _voices[name] = PiperVoice.load(model_path, config_path=config_path)
    return _voices[name]


@app.route("/synthesize", methods=["POST"])
def synthesize():
    data = request.get_json(force=True)
    text = data.get("text", "")
    voice_name = data.get("voice", DEFAULT_VOICE)

    if not text:
        return jsonify({"error": "No text provided"}), 400

    try:
        voice = _get_voice(voice_name)
    except FileNotFoundError:
        return jsonify({"error": f"Voice model '{voice_name}' not found in {MODEL_DIR}"}), 404

    try:
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wav:
            # Let Piper set channels/sample rate/width — do NOT pre-set them
            voice.synthesize_wav(text, wav)

        audio_data = buf.getvalue()
        log.info("Synthesized %d bytes for: %s", len(audio_data), text[:80])

        return Response(audio_data, mimetype="audio/wav")

    except Exception as e:
        log.exception("Piper synthesis failed")
        return jsonify({"error": str(e)}), 500


@app.route("/health")
def health():
    return jsonify({"status": "ok", "default_voice": DEFAULT_VOICE})


if __name__ == "__main__":
    log.info("Pre-loading default voice: %s", DEFAULT_VOICE)
    _get_voice(DEFAULT_VOICE)
    log.info("Piper TTS server ready on :5000")
    app.run(host="0.0.0.0", port=5000)
