"""
CalendarContext — fetches calendar events, caches them, and
formats them as natural language for LLM system prompt injection.
"""
import time
import logging
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from collections import defaultdict

from providers.base import CalendarProvider
from services.token_store import TokenStore

log = logging.getLogger(__name__)


class CalendarContext:
    def __init__(self, provider: CalendarProvider, token_store: TokenStore,
                 config: dict):
        self.provider = provider
        self.token_store = token_store
        self.timezone = config.get("timezone", "America/Denver")
        self.lookahead_days = config.get("lookahead_days", 3)
        self.cache_ttl = config.get("cache_ttl_minutes", 5) * 60
        self.context_mode = config.get("context_mode", "inject")

        # In-memory cache
        self._cached_events: list[dict] | None = None
        self._cache_timestamp: float = 0

    @property
    def enabled(self) -> bool:
        return self.context_mode == "inject"

    def get_context_string(self) -> str:
        """
        Return formatted calendar context for injection into system prompt.
        Returns empty string if disabled, unauthenticated, or no events.
        """
        if not self.enabled:
            return ""

        if not self.provider.is_authenticated(self.token_store):
            log.debug("Calendar: not authenticated, skipping context")
            return ""

        events = self._get_cached_events()
        return self._format_events(events)

    def _get_cached_events(self) -> list[dict]:
        """Fetch events with caching."""
        now = time.time()

        if self._cached_events is not None and (now - self._cache_timestamp) < self.cache_ttl:
            log.debug("Calendar: using cached events (%d sec old)",
                      int(now - self._cache_timestamp))
            return self._cached_events

        tz = ZoneInfo(self.timezone)
        start = datetime.now(tz)
        end = start + timedelta(days=self.lookahead_days)

        try:
            events = self.provider.get_events(start, end, self.token_store)
            self._cached_events = events
            self._cache_timestamp = now
            log.info("Calendar: cached %d events (TTL: %ds)",
                     len(events), self.cache_ttl)
        except Exception as e:
            log.warning("Calendar: fetch failed (%s), using stale cache", e)
            if self._cached_events is not None:
                return self._cached_events
            return []

        return events

    def invalidate_cache(self):
        """Force next call to refetch events."""
        self._cached_events = None
        self._cache_timestamp = 0

    def _format_events(self, events: list[dict]) -> str:
        """Format events as natural language for the LLM."""
        tz = ZoneInfo(self.timezone)
        now = datetime.now(tz)

        lines = [
            "",
            f"Current date and time: {now.strftime('%A, %B %d, %Y, %I:%M %p')} ({self.timezone})",
            "",
        ]

        if not events:
            lines.append(f"Your calendar is clear for the next {self.lookahead_days} days.")
            return "\n".join(lines)

        lines.append(f"Your schedule for the next {self.lookahead_days} days:")
        lines.append("")

        # Group events by date
        by_day: dict[str, list[str]] = defaultdict(list)

        for event in events:
            if event["all_day"]:
                event_date = datetime.fromisoformat(event["start"]).date()
                time_str = "All day"
            else:
                start_dt = datetime.fromisoformat(event["start"])
                if start_dt.tzinfo is None:
                    start_dt = start_dt.replace(tzinfo=tz)
                else:
                    start_dt = start_dt.astimezone(tz)
                event_date = start_dt.date()

                end_dt = datetime.fromisoformat(event["end"])
                if end_dt.tzinfo is None:
                    end_dt = end_dt.replace(tzinfo=tz)
                else:
                    end_dt = end_dt.astimezone(tz)

                time_str = (
                    f"{start_dt.strftime('%-I:%M %p')} – "
                    f"{end_dt.strftime('%-I:%M %p')}"
                )

            summary = event["summary"]
            location = event.get("location", "")
            entry = f"  - {time_str}: {summary}"
            if location:
                entry += f" ({location})"

            by_day[event_date.isoformat()].append(entry)

        # Format each day in the lookahead window
        for day_offset in range(self.lookahead_days):
            date = (now + timedelta(days=day_offset)).date()
            date_key = date.isoformat()

            if day_offset == 0:
                label = f"Today ({date.strftime('%A, %B %d')})"
            elif day_offset == 1:
                label = f"Tomorrow ({date.strftime('%A, %B %d')})"
            else:
                label = date.strftime("%A, %B %d")

            if date_key in by_day:
                lines.append(f"{label}:")
                lines.extend(by_day[date_key])
            else:
                lines.append(f"{label}: No events")

            lines.append("")

        return "\n".join(lines)
