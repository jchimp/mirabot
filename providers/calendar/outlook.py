"""
Outlook.com Calendar provider — stub for v1.3.

Will use MSAL device code flow + Microsoft Graph API.
"""
import logging

from providers.base import CalendarProvider
from providers.factory import register

log = logging.getLogger(__name__)


@register("calendar", "outlook")
class OutlookCalendar(CalendarProvider):

    def __init__(self, config: dict):
        super().__init__(config)
        self.client_id = config.get("client_id", "")
        self.tenant = config.get("tenant", "consumers")
        self.scopes = config.get("scopes", ["Calendars.Read"])

    def authenticate_interactive(self, token_store) -> bool:
        # TODO: Implement MSAL device code flow
        # 1. Create PublicClientApplication with client_id + authority
        # 2. initiate_device_flow(scopes)
        # 3. Print user_code + verification_uri
        # 4. acquire_token_by_device_flow()
        # 5. Store in token_store
        print("\n⚠️  Outlook calendar support is coming in v1.3!")
        print("   Use 'google' provider for now.\n")
        return False

    def get_events(self, start, end, token_store) -> list[dict]:
        log.warning("Outlook calendar not yet implemented")
        return []

    def is_authenticated(self, token_store) -> bool:
        return False
