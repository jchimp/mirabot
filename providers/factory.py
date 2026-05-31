"""
Provider registry + factory.
Adding a new provider = write the class, add ONE line to the registry.
"""
from providers.base import STTProvider, TTSProvider, LLMProvider, CalendarProvider

# ── Registry ─────────────────────────────────────────────
_REGISTRY: dict[str, dict[str, type]] = {
    "stt": {},
    "tts": {},
    "llm": {},
    "calendar": {},
}


def register(service_type: str, name: str):
    """Decorator to register a provider class."""
    def decorator(cls):
        _REGISTRY[service_type][name] = cls
        return cls
    return decorator


def _build(service_type: str, config: dict):
    """Instantiate a provider from config."""
    name = config.get("provider", "")
    registry = _REGISTRY.get(service_type, {})
    cls = registry.get(name)
    if cls is None:
        available = ", ".join(registry.keys()) or "(none)"
        raise ValueError(
            f"Unknown {service_type} provider '{name}'. Available: {available}"
        )
    return cls(config)


def create_providers(config: dict) -> dict:
    """
    Read full app config, return dict of instantiated providers.
    Calendar is optional — returns None if provider is "none" or missing.
    """
    # Force import so @register decorators run
    import providers.stt.faster_whisper   # noqa: F401
    import providers.stt.openai_stt       # noqa: F401
    import providers.tts.piper            # noqa: F401
    import providers.tts.openai_tts       # noqa: F401
    import providers.llm.ollama           # noqa: F401
    import providers.llm.openai_llm       # noqa: F401
    import providers.calendar.google_cal  # noqa: F401
    import providers.calendar.outlook     # noqa: F401

    result = {
        "stt": _build("stt", config.get("stt", {})),
        "tts": _build("tts", config.get("tts", {})),
        "llm": _build("llm", config.get("llm", {})),
    }

    # Calendar is optional
    cal_config = config.get("calendar", {})
    cal_provider = cal_config.get("provider", "none")
    if cal_provider and cal_provider.lower() != "none":
        result["calendar"] = _build("calendar", cal_config)
    else:
        result["calendar"] = None

    return result