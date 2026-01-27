# JohnnyBets Infrastructure

Azure infrastructure for JohnnyBets using Bicep templates.

## Live URLs

| Domain | Points To |
|--------|-----------|
| [johnnybets.ai](https://johnnybets.ai) | Static Web App (frontend) |
| [www.johnnybets.ai](https://www.johnnybets.ai) | Static Web App (frontend) |
| [api.johnnybets.ai](https://api.johnnybets.ai) | Container App (API) |

## Architecture

```
                    ┌─────────────────┐
                    │   Cloudflare    │
                    │   (WAF/CDN)     │
                    └────────┬────────┘
                             │
              ┌──────────────┴──────────────┐
              │                              │
    ┌─────────▼─────────┐        ┌──────────▼──────────┐
    │  Static Web App   │        │  Container Apps     │
    │  (swa-jbet-web)   │───────▶│  (ca-jbet-api)      │
    └───────────────────┘        └──────────┬──────────┘
                                            │
                          ┌─────────────────┼─────────────────┐
                          │                 │                 │
                ┌─────────▼────┐  ┌─────────▼────┐  ┌─────────▼────┐
                │  PostgreSQL  │  │  Key Vault   │  │ Log Analytics│
                │  (psql-jbet) │  │  (kv-jbet)   │  │  (log-jbet)  │
                └──────────────┘  └──────────────┘  └──────────────┘
```

## Naming Convention

Pattern: `{prefix}-{app}-{service}-{env}-{region}`

| Component | Value |
|-----------|-------|
| App abbreviation | `jbet` |
| Region | `eus2` (East US 2) |
| Environment | `prod` |

### Resource Names

| Resource Type | Prefix | Full Name |
|--------------|--------|-----------|
| Resource Group | `rg-` | `rg-johnnybets-prod-eus2` |
| Container Registry | `cr` | `crjohnnybets` (global) |
| Container App Environment | `cae-` | `cae-jbet-prod-eus2` |
| Container App | `ca-` | `ca-jbet-api-prod-eus2` |
| Static Web App | `swa-` | `swa-jbet-web-prod-eus2` |
| PostgreSQL | `psql-` | `psql-jbet-prod-eus2` |
| Key Vault | `kv-` | `kv-jbet-prod-eus2` |
| Log Analytics | `log-` | `log-jbet-prod-eus2` |

### Tags

All resources include standard tags:
```json
{
  "environment": "prod",
  "project": "johnnybets",
  "managedBy": "bicep"
}
```

## Prerequisites

1. Azure CLI installed and logged in (`az login`)
2. Azure subscription with Contributor access
3. GitHub repository with secrets configured

## Bicep Structure

```
infrastructure/
├── bicep/
│   ├── main.bicep                    # Main orchestration
│   ├── modules/
│   │   ├── containerRegistry.bicep   # Azure Container Registry
│   │   ├── containerAppEnv.bicep     # Container Apps Environment
│   │   ├── containerApp.bicep        # Container App (API)
│   │   ├── staticWebApp.bicep        # Static Web App (Frontend)
│   │   ├── postgresql.bicep          # PostgreSQL Flexible Server
│   │   ├── keyVault.bicep            # Key Vault for secrets
│   │   └── logAnalytics.bicep        # Log Analytics workspace
│   └── parameters/
│       └── prod.parameters.json      # Production parameters
└── cloudflare/
    └── waf-rules.json                # Cloudflare WAF configuration
```

## Deployment

### First Time Setup

#### 1. Create Service Principal

```bash
# Replace {subscription-id} with your Azure subscription ID
az ad sp create-for-rbac \
  --name "sp-jbet-github" \
  --role contributor \
  --scopes /subscriptions/{subscription-id} \
  --sdk-auth
```

Save the JSON output - this is your `AZURE_CREDENTIALS` GitHub secret.

#### 2. Create Resource Group

```bash
az group create \
  --name rg-johnnybets-prod-eus2 \
  --location eastus2
```

#### 3. Deploy Infrastructure

```bash
az deployment group create \
  --resource-group rg-johnnybets-prod-eus2 \
  --template-file bicep/main.bicep \
  --parameters @bicep/parameters/prod.parameters.json
```

#### 4. Get Deployment Outputs

```bash
# Get Container Registry login server
az acr show \
  --name crjohnnybets \
  --query loginServer \
  --output tsv

# Get Container Registry credentials
az acr credential show \
  --name crjohnnybets \
  --query "{username:username, password:passwords[0].value}"

# Get Static Web App deployment token
az staticwebapp secrets list \
  --name swa-jbet-web-prod-eus2 \
  --query "properties.apiKey" \
  --output tsv
```

#### 5. Configure GitHub Secrets

Add these secrets to your GitHub repository:

| Secret | Value |
|--------|-------|
| `AZURE_CREDENTIALS` | Service principal JSON from step 1 |
| `AZURE_SUBSCRIPTION_ID` | Your Azure subscription ID |
| `ACR_LOGIN_SERVER` | `crjohnnybets.azurecr.io` |
| `ACR_USERNAME` | From step 4 |
| `ACR_PASSWORD` | From step 4 |
| `AZURE_STATIC_WEB_APPS_API_TOKEN` | From step 4 |
| `OPENROUTER_API_KEY` | Your OpenRouter API key |
| `THE_ODDS_API_KEY` | Your The Odds API key |

### Subsequent Deployments

After initial setup, deployments are automated:

- **Push to `main`** → Deploys API and Web
- **Manual workflow** → Run `deploy-infrastructure.yml` for infra changes

### Update Infrastructure

```bash
# Preview changes
az deployment group what-if \
  --resource-group rg-johnnybets-prod-eus2 \
  --template-file bicep/main.bicep \
  --parameters @bicep/parameters/prod.parameters.json

# Apply changes
az deployment group create \
  --resource-group rg-johnnybets-prod-eus2 \
  --template-file bicep/main.bicep \
  --parameters @bicep/parameters/prod.parameters.json
```

## Key Vault Secrets

The following secrets are stored in Key Vault and referenced by Container Apps:

| Secret Name | Description |
|-------------|-------------|
| `openrouter-api-key` | OpenRouter API key for LLM access |
| `odds-api-key` | The Odds API key for sportsbook odds |
| `database-url` | PostgreSQL connection string (auto-generated) |
| `nextauth-secret` | NextAuth.js session encryption key |

### Adding Secrets

```bash
# Add a secret to Key Vault
az keyvault secret set \
  --vault-name kv-jbet-prod-eus2 \
  --name "openrouter-api-key" \
  --value "your-api-key"
```

## Database

### Connection String

```
postgresql://{admin}:{password}@psql-jbet-prod-eus2.postgres.database.azure.com:5432/johnnybets?sslmode=require
```

### Run Migrations

```bash
# From web/ directory
DATABASE_URL="postgresql://..." npx prisma db push
```

## Cloudflare Configuration

The `cloudflare/` directory contains WAF and security rules:

- **Bot Protection** - Challenges suspicious traffic
- **Rate Limiting** - 100 req/min for API, 20 req/min for auth
- **Firewall Rules** - Block known bad actors
- **Security Headers** - CSP, HSTS, etc.

Apply rules via Cloudflare dashboard or API.

## Monitoring

### Log Analytics

All services send logs to `log-jbet-prod-eus2`. Query logs:

```kusto
// Container App logs
ContainerAppConsoleLogs_CL
| where ContainerAppName_s == "ca-jbet-api-prod-eus2"
| order by TimeGenerated desc
| take 100
```

### Health Checks

- API: `https://ca-jbet-api-prod-eus2.{region}.azurecontainerapps.io/health`
- Web: `https://swa-jbet-web-prod-eus2.azurestaticapps.net`

## Cost Estimation

| Resource | SKU | Estimated Monthly |
|----------|-----|-------------------|
| Container Registry | Basic | ~$5 |
| Container Apps | Consumption | ~$20-50 |
| Static Web Apps | Free/Standard | $0-$9 |
| PostgreSQL | Burstable B1ms | ~$15 |
| Key Vault | Standard | ~$1 |
| Log Analytics | Pay-as-you-go | ~$5 |
| **Total** | | **~$50-85/month** |

## Troubleshooting

### Container App not starting

```bash
# Check logs
az containerapp logs show \
  --name ca-jbet-api-prod-eus2 \
  --resource-group rg-johnnybets-prod-eus2 \
  --follow
```

### Database connection issues

1. Check firewall rules allow Container App outbound
2. Verify connection string in Key Vault
3. Ensure SSL mode is set to `require`

### Static Web App 404s

1. Check `staticwebapp.config.json` for routing rules
2. Verify build output directory is correct
3. Check API proxy configuration
