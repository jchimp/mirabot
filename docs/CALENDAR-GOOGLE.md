# Google Calendar Authentication Setup

## 🚀 Setup Instructions

### 1. Google Cloud Setup (one time)
1. Go to https://console.cloud.google.com
2. Create a new project (or use existing)
3. Enable the "Google Calendar API":
    → APIs & Services → Library → search "Google Calendar API" → Enable
4. Configure OAuth consent screen:
    → APIs & Services → OAuth consent screen
    → User Type: External → Create
    → App name: "Mirror" → Add your email as test user → Save
5. Create credentials:
    → APIs & Services → Credentials → Create Credentials → OAuth client ID
    → Application type: "Desktop app"
    → Name: "Mirror Calendar"
    → Create
6. Copy the Client ID and Client Secret into your config.yaml

### 2. Update config.yaml
```
calendar:
  provider: "google"
  client_id: "123456789-abc123.apps.googleusercontent.com"
  client_secret: "GOCSPX-your-actual-secret"
  scopes:
    - "https://www.googleapis.com/auth/calendar.readonly"
  lookahead_days: 3
  cache_ttl_minutes: 5
  timezone: "America/Denver"
  context_mode: "inject"
```

### 3. Rebuild and run
```
docker compose build --no-cache mirror
docker compose up -d mirror
```

### 4. Authenticate
```
docker exec -it mirror flask calendar-setup
```
You'll see:
```
Setting up calendar: google
----------------------------------------

============================================================
  Google Calendar — Authorization
============================================================

A browser window should open. If not, visit the URL below.
After authorizing, you'll be redirected back automatically.

Please visit this URL to authorize this application:
https://accounts.google.com/o/oauth2/auth?client_id=...&scope=...

✅ Google Calendar authorized successfully!
   Tokens stored and encrypted.

📅 Found 3 events today:
   - Daily Standup
   - 1:1 with Andrea
   - IT Infrastructure Review
```

### 5. Verify
```
# Check status
docker exec -it mirror flask calendar-status

# Check health endpoint
curl http://localhost:5000/api/health | python -m json.tool
```

### 6. Test it

Talk to your mirror:

"What's on my calendar today?"
"Am I free at 2pm?"
"What does tomorrow look like?"
"Do I have any meetings this afternoon?"

The LLM already has your schedule in context — it just answers naturally.


## Security Notes

- Tokens are encrypted at rest (Fernet/AES) in SQLite — change your FLASK_SECRET_KEY to something strong
- Calendar access is read-only — the mirror can never create, modify, or delete events
- Port 8090 is only needed during setup — you can remove the mapping from docker-compose after authenticating
- Refresh tokens auto-renew — you shouldn't need to re-authenticate unless you revoke access

That's the complete calendar integration. The architecture follows the same provider pattern you already know — when you're ready for Outlook, just fill in outlook.py with the MSAL device code flow and change one line in config.yaml. 