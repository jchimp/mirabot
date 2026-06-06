"""
Google Calendar provider — read-only access via OAuth 2.0.

Setup: flask calendar-setup
Auth flow: InstalledAppFlow (local server on port 8090)
"""
import logging
from datetime import datetime

from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from google_auth_oauthlib.flow import InstalledAppFlow

from providers.base import CalendarProvider
from providers.factory import register

log = logging.getLogger(__name__)

PROVIDER_NAME = "google"


@register("calendar", "google")
class GoogleCalendar(CalendarProvider):

    def __init__(self, config: dict):
        super().__init__(config)
        self.client_id = config.get("client_id", "")
        self.client_secret = config.get("client_secret", "")
        self.scopes = config.get("scopes", [
            "https://www.googleapis.com/auth/calendar.readonly"
        ])
        self._service = None        # cached API service object
        self._service_creds = None  # credentials used to build it

    # ── Auth ─────────────────────────────────────

    def authenticate_interactive(self, token_store) -> bool:
        """
        Run OAuth 2.0 InstalledAppFlow with a local callback server.
        The user visits the printed URL, authorizes, and Google
        redirects back to localhost:8090 where we catch the code.
        """
        client_config = {
            "installed": {
                "client_id": self.client_id,
                "client_secret": self.client_secret,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": ["http://localhost:8090"],
            }
        }

        flow = InstalledAppFlow.from_client_config(client_config, self.scopes)

        print("\n" + "=" * 60)
        print("  Google Calendar — Authorization")
        print("=" * 60)
        print("\nA browser window should open. If not, visit the URL below.")
        print("After authorizing, you'll be redirected back automatically.\n")

        creds = flow.run_local_server(
            port=8090,
            bind_addr="0.0.0.0",
            open_browser=False,
            prompt="consent",
            access_type="offline",
        )

        # Serialize and store
        token_data = {
            "token": creds.token,
            "refresh_token": creds.refresh_token,
            "token_uri": creds.token_uri,
            "client_id": creds.client_id,
            "client_secret": creds.client_secret,
            "scopes": list(creds.scopes or []),
            "expiry": creds.expiry.isoformat() if creds.expiry else None,
        }
        token_store.save_token(PROVIDER_NAME, token_data)

        print("\n✅ Google Calendar authorized successfully!")
        print("   Tokens stored and encrypted.\n")
        return True

    def is_authenticated(self, token_store) -> bool:
        """Check if we have tokens that are valid or refreshable."""
        creds = self._get_credentials(token_store)
        return creds is not None

    # ── Events ───────────────────────────────────

    def get_events(self, start: datetime, end: datetime, token_store) -> list[dict]:
        """Fetch events from Google Calendar in the given range."""
        creds = self._get_credentials(token_store)
        if not creds:
            log.warning("Google Calendar: no valid credentials")
            return []

        try:
            # Rebuild the service only when credentials change (e.g. after a token refresh)
            if self._service is None or self._service_creds is not creds:
                self._service = build("calendar", "v3", credentials=creds,
                                      cache_discovery=False)
                self._service_creds = creds

            events_result = (
                service.events()
                .list(
                    calendarId="primary",
                    timeMin=start.isoformat(),
                    timeMax=end.isoformat(),
                    singleEvents=True,
                    orderBy="startTime",
                    maxResults=50,
                )
                .execute()
            )

            events = []
            for item in events_result.get("items", []):
                is_all_day = "date" in item.get("start", {})
                events.append({
                    "summary": item.get("summary", "(No title)"),
                    "start": item["start"].get("dateTime", item["start"].get("date", "")),
                    "end": item["end"].get("dateTime", item["end"].get("date", "")),
                    "location": item.get("location", ""),
                    "all_day": is_all_day,
                })

            log.info("Google Calendar: fetched %d events (%s to %s)",
                     len(events), start.date(), end.date())
            return events

        except Exception as e:
            log.exception("Google Calendar fetch failed")
            return []

    # ── Internal ─────────────────────────────────

    def _get_credentials(self, token_store) -> Credentials | None:
        """Load credentials from token store, refresh if expired."""
        token_data = token_store.get_token(PROVIDER_NAME)
        if not token_data:
            return None

        creds = Credentials(
            token=token_data.get("token"),
            refresh_token=token_data.get("refresh_token"),
            token_uri=token_data.get("token_uri", "https://oauth2.googleapis.com/token"),
            client_id=token_data.get("client_id"),
            client_secret=token_data.get("client_secret"),
            scopes=token_data.get("scopes"),
        )

        # Refresh if expired
        if creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save the refreshed token
                token_data["token"] = creds.token
                token_data["expiry"] = creds.expiry.isoformat() if creds.expiry else None
                token_store.save_token(PROVIDER_NAME, token_data)
                log.info("Google Calendar: token refreshed")
            except Exception as e:
                log.error("Google Calendar: token refresh failed: %s", e)
                return None

        return creds
