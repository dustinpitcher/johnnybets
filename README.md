# JohnnyBets

AI-powered sports betting analysis with real-time odds, arbitrage detection, and contextual prop analysis.

**Live:** [johnnybets.ai](https://johnnybets.ai) | **API:** [api.johnnybets.ai](https://api.johnnybets.ai/health)

## Features

### Free Tools (Available Now)

**General**
- Live Odds - Real-time odds from 10+ sportsbooks (DraftKings, FanDuel, BetMGM, etc.)
- Arbitrage Scanner - Find guaranteed profit opportunities
- X/Twitter Intel - Breaking news, injury updates, line movement
- Edge Validator - Anti-slop validation before betting

**NFL**
- Prop Alpha - Contextual player prop analysis with defense profiling
- Defense Profiler - Data-driven defensive metrics
- Weather Splits - Player performance by weather conditions
- Game Script Splits - Performance when winning/losing

**NHL**
- Goalie Alpha - Goalie props with B2B splits and xGSV%
- Team Analytics - Corsi, xG, possession metrics
- Matchup Analyzer - Head-to-head edge identification
- Referee Tendencies - Penalty/over tendencies by ref crew

**MLB**
- Pitcher Alpha - K projections, IP estimates, Stuff+, pitch mix analysis
- Pitcher Profile - Detailed metrics with platoon splits
- Lineup vs Pitcher - xwOBA, K rates, barrel rates by batter
- Park Factors - All 30 stadiums with run/HR/K factors
- Bullpen Analyzer - Relief arm availability and fatigue tracking
- Weather Impact - Wind/temp effects on totals

### Coming Soon
- Sharps Consensus - Professional money flow
- Line Movement Alerts - Real-time notifications

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker (for PostgreSQL)
- OpenRouter API key ([get one here](https://openrouter.ai))
- The Odds API key ([get one here](https://the-odds-api.com))

### Installation

```bash
# Clone the repository
git clone https://github.com/johnnybets/johnnybets.git
cd johnnybets

# Copy environment variables
cp .env.example .env
# Edit .env with your API keys

# Create Python virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install Python dependencies
pip install -r requirements.txt

# Install web dependencies
cd web
npm install
cd ..
```

### Database Setup

JohnnyBets uses PostgreSQL for storing user sessions, chat history, and settings.

```bash
# Start PostgreSQL with Docker
docker compose up -d postgres

# Run database migrations
cd web
npx prisma db push
npx prisma generate
cd ..
```

The database will be available at `postgresql://postgres:postgres@localhost:5432/johnnybets`.

### Running Locally

```bash
# Terminal 1: Start the API
source venv/bin/activate
uvicorn api.main:app --reload --port 8000

# Terminal 2: Start the web frontend
cd web
npm run dev
```

Visit http://localhost:3000 to use the app.

### Using Docker (Full Stack)

```bash
# Start all services (API, Web, PostgreSQL)
docker compose up
```

## Project Structure

```
johnnybets/
├── api/                    # FastAPI backend
│   ├── main.py             # App entry point
│   ├── routes/
│   │   ├── chat.py         # Chat endpoints
│   │   ├── tools.py        # Tool registry endpoints
│   │   ├── entities.py     # Entity extraction
│   │   ├── scores.py       # Live scores
│   │   └── payments.py     # Stripe/TrySpeed
│   └── core/
│       ├── agent.py        # LangGraph agent
│       ├── tool_registry.py
│       └── entity_extraction.py
├── web/                    # Next.js frontend
│   ├── app/
│   │   ├── page.tsx        # Terminal UI
│   │   ├── tools/page.tsx  # Tools showcase
│   │   ├── settings/page.tsx # User settings (BYOK)
│   │   └── api/            # Next.js API routes
│   ├── components/
│   │   ├── Terminal.tsx
│   │   ├── Ticker.tsx
│   │   └── Modal.tsx
│   ├── prisma/
│   │   └── schema.prisma   # Database schema
│   └── lib/
│       ├── api.ts          # API client
│       ├── auth.ts         # NextAuth config
│       └── sessions.ts     # Session management
├── src/                    # Core analysis tools
│   ├── tools/              # Data fetchers
│   │   ├── mlb_data.py     # MLB pitcher analysis
│   │   ├── nfl_data.py     # NFL data
│   │   └── nhl_data.py     # NHL data
│   └── analysis/           # Analysis modules
├── infrastructure/         # Azure IaC (Bicep)
│   ├── bicep/              # Bicep templates
│   └── cloudflare/         # WAF rules
└── .github/workflows/      # CI/CD
```

## Environment Variables

See [.env.example](.env.example) for all available environment variables.

**Required:**
- `OPENROUTER_API_KEY` - LLM access
- `THE_ODDS_API_KEY` - Sportsbook odds
- `DATABASE_URL` - PostgreSQL connection
- `NEXTAUTH_SECRET` - Session encryption
- `NEXTAUTH_URL` - App URL

## API Endpoints

### Chat
- `POST /api/chat/sessions` - Create new session
- `POST /api/chat/sessions/{id}/stream` - Send message (streaming)
- `POST /api/chat/quick/stream` - Quick chat with auto-session

### Tools
- `GET /api/tools` - List all tools
- `GET /api/tools/stats` - Tool statistics
- `POST /api/tools/{id}/vote` - Vote for idea tools

### Entities
- `POST /api/entities/extract` - Extract teams/players from text

### Scores
- `GET /api/scores?sport=nfl` - Live scores by sport

## Deployment

JohnnyBets deploys to Azure using GitHub Actions and Bicep infrastructure as code.

### Azure Resources

| Resource | Name |
|----------|------|
| Resource Group | `rg-johnnybets-prod-eus2` |
| Container Registry | `crjohnnybets` |
| Container App (API) | `ca-jbet-api-prod-eus2` |
| Static Web App | `swa-jbet-web-prod-eus2` |
| PostgreSQL | `psql-jbet-prod-eus2` |
| Key Vault | `kv-jbet-prod-eus2` |

### GitHub Secrets Required

- `AZURE_CREDENTIALS` - Service principal JSON
- `AZURE_SUBSCRIPTION_ID` - Azure subscription ID
- `ACR_LOGIN_SERVER` - `crjohnnybets.azurecr.io`
- `ACR_USERNAME` / `ACR_PASSWORD` - Registry credentials
- `AZURE_STATIC_WEB_APPS_API_TOKEN` - SWA deployment token
- `OPENROUTER_API_KEY` - For API container
- `THE_ODDS_API_KEY` - For API container

### Deploy Infrastructure

```bash
# First time: Deploy Azure resources
az deployment group create \
  --resource-group rg-johnnybets-prod-eus2 \
  --template-file infrastructure/bicep/main.bicep \
  --parameters @infrastructure/bicep/parameters/prod.parameters.json
```

See [infrastructure/README.md](infrastructure/README.md) for detailed deployment instructions.

## CLI Usage (Development)

The original CLI is still available for testing:

```bash
# Interactive chat
python src/main.py chat

# With specific model
python src/main.py chat --model grok-fast

# Prop analysis
python src/main.py props "Josh Allen" DEN --yards 265.5
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.

---

Built with care for sports bettors who want an edge.
