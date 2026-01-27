# Kalshi Setup Instructions

Kalshi provides prediction market data for sports betting. The integration uses RSA-PSS authentication.

> **Note:** For production, users can connect their own Kalshi credentials via the Settings page (BYOK - Bring Your Own Key). These instructions are for development/testing.

## Option 1: Use Public API (No Auth Required)

The Kalshi public API works without authentication for reading market data. No setup needed - the `fetch_kalshi_markets` tool works out of the box.

## Option 2: Authenticated API (For Advanced Features)

For features like portfolio viewing or placing trades, you need API credentials.

### 1. Generate Keys

1. Log in to [Kalshi](https://kalshi.com)
2. Go to **Account & Security** -> **API Keys**
3. Click **Create Key**
4. This will download a `.key` file (your private key) and show you a Key ID

### 2. Update Environment Variables

Add the following to your `.env` file in the project root:

```bash
KALSHI_API_KEY=your_key_id_here
KALSHI_PRIVATE_KEY_FILE=./kalshi.key
```

Or store the key contents directly (useful for production):

```bash
KALSHI_API_KEY=your_key_id_here
KALSHI_PRIVATE_KEY=-----BEGIN PRIVATE KEY-----
...key contents...
-----END PRIVATE KEY-----
```

### 3. Verify

Start the API and test the Kalshi tool:

```bash
# Start the API
uvicorn api.main:app --reload --port 8000

# In another terminal, test the endpoint
curl http://localhost:8000/api/chat/quick \
  -H "Content-Type: application/json" \
  -d '{"message": "Show me NFL prediction markets on Kalshi"}'
```

## Production Setup (BYOK)

In production, users connect their own Kalshi credentials:

1. Sign in to JohnnyBets
2. Go to Settings
3. Click "Connect Kalshi"
4. Enter your API Key ID and private key contents
5. Credentials are encrypted and stored securely

This allows each user to use their own Kalshi account without sharing credentials.
