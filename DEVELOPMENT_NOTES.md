# JohnnyBets Development Notes

> Lessons learned and common pitfalls to avoid. Read this before making infrastructure or deployment changes.

## GitHub Actions & Deployments

### DO NOT use `azure/container-apps-deploy-action` with `environmentVariables`
The action **REPLACES ALL env vars**, not merges them. This breaks production.

```yaml
# BAD - will wipe all existing env vars
- uses: azure/container-apps-deploy-action@v2
  with:
    environmentVariables: |
      FOO=bar

# GOOD - only updates the image, preserves env vars
- run: |
    az containerapp update \
      --name ${{ env.CONTAINER_APP_NAME }} \
      --resource-group ${{ env.RESOURCE_GROUP }} \
      --image ${{ env.REGISTRY }}/${{ env.IMAGE_NAME }}:${{ github.sha }}
```

### Env vars and secrets are managed separately
- Set via Azure CLI or Portal, NOT through CI/CD
- Secrets use `secretref:secret-name` syntax
- Run this to restore if accidentally wiped:
```bash
az containerapp update \
  --name ca-jbet-api-prod-eus2 \
  --resource-group rg-johnnybets-prod-eus2 \
  --set-env-vars \
    "OPENROUTER_API_KEY=secretref:openrouter-api-key" \
    "ODDS_API_KEY=secretref:odds-api-key" \
    "THE_ODDS_API_KEY=secretref:odds-api-key" \
    "DATABASE_URL=secretref:database-url" \
    "BETTING_AGENT_MODEL=x-ai/grok-4.1-fast"
```

### Docker buildx caching
The default docker driver doesn't support GHA caching. Either:
1. Add `driver: docker-container` to setup-buildx-action
2. Or just remove cache options (simpler, slightly slower builds)

```yaml
# If using caching:
- uses: docker/setup-buildx-action@v3
  with:
    driver: docker-container

# Or just remove cache-from/cache-to entirely
```

---

## Next.js / Frontend

### `NEXT_PUBLIC_*` variables are baked at BUILD time
These are NOT runtime variables. They must be available during `npm run build`.

For Docker:
```dockerfile
ARG NEXT_PUBLIC_API_URL=https://api.johnnybets.ai
ENV NEXT_PUBLIC_API_URL=${NEXT_PUBLIC_API_URL}
RUN npm run build
```

### `.env.local` overrides `.env.production`
Add `.env.local` to `.dockerignore` to prevent local dev config from breaking production builds:
```
# web/.dockerignore
.env.local
.env.*.local
```

---

## Azure Container Apps

### Cold starts - set minReplicas to 1
Default is 0, which causes timeouts when the app scales down:
```bash
az containerapp update \
  --name ca-jbet-api-prod-eus2 \
  --resource-group rg-johnnybets-prod-eus2 \
  --min-replicas 1
```

### Checking logs
```bash
# Console logs (application output)
az containerapp logs show \
  --name ca-jbet-api-prod-eus2 \
  --resource-group rg-johnnybets-prod-eus2 \
  --tail 50

# System logs (startup, crashes)
az containerapp logs show \
  --name ca-jbet-api-prod-eus2 \
  --resource-group rg-johnnybets-prod-eus2 \
  --type system \
  --tail 30
```

### Platform must be linux/amd64
Azure Container Apps requires amd64. Always specify platform:
```bash
docker buildx build --platform linux/amd64 ...
```

---

## Python / API

### Keep production dependencies in sync
If a module imports a package, it MUST be in `requirements.txt` (not just `requirements-dev.txt`).

Common culprits:
- `rich` - used for console formatting in analysis modules
- `typer` - CLI tools
- `playwright` - browser automation (should stay dev-only)

### NFL team name normalization
The nflverse data uses abbreviations (NE, SEA, BUF) but user queries use full names.
The `normalize_team()` function in `src/tools/nfl_data.py` handles this.

### PBP data caching
The `NFLDataFetcher` caches combined PBP data. Without this, analysis calls load data 40+ times.
- Cache key is based on years tuple: `(2024, 2025)`
- First load prints "Loading...", subsequent calls are silent

---

## Debugging Checklist

When something breaks in production:

1. **Check API health first**
   ```bash
   curl https://api.johnnybets.ai/health
   ```

2. **Check container status**
   ```bash
   az containerapp replica list \
     --name ca-jbet-api-prod-eus2 \
     --resource-group rg-johnnybets-prod-eus2 \
     --query "[].{name:name, state:properties.runningState}" -o table
   ```

3. **Check logs for errors**
   ```bash
   az containerapp logs show ... --type console | grep -i error
   ```

4. **Check env vars are set**
   ```bash
   az containerapp show \
     --name ca-jbet-api-prod-eus2 \
     --resource-group rg-johnnybets-prod-eus2 \
     --query "properties.template.containers[0].env" -o table
   ```

5. **Test locally first** before deploying fixes

---

## Common Errors & Fixes

| Error | Cause | Fix |
|-------|-------|-----|
| `401 - No cookie auth credentials found` | Missing OPENROUTER_API_KEY | Restore env vars (see above) |
| `startup probe failed: connection refused` | Container crash loop | Check console logs for import/runtime errors |
| `ModuleNotFoundError: rich` | Dev dependency used in prod | Add to requirements.txt |
| Ticker shows "Unable to load scores" | NEXT_PUBLIC_API_URL not set at build | Check .dockerignore, rebuild |
| `Cache export is not supported` | Docker buildx driver issue | Remove cache options or fix driver |

---

## Resource Naming Convention

```
{prefix}-{app}-{service}-{env}-{region}

Examples:
- rg-johnnybets-prod-eus2 (resource group)
- ca-jbet-api-prod-eus2 (container app - API)
- ca-jbet-web-prod-eus2 (container app - Web)
- psql-jbet-prod-eus2 (PostgreSQL)
- kv-jbet-prod-eus2 (Key Vault)
- crjohnnybets (Container Registry - no hyphens allowed)
```

---

## Useful Commands

```bash
# Local development
cd johnnybets
python -m uvicorn api.main:app --port 8000 --reload

# Test production API
curl -s -X POST https://api.johnnybets.ai/api/chat/quick \
  -H "Content-Type: application/json" \
  -d '{"message": "test"}'

# Force restart container
az containerapp revision restart \
  --name ca-jbet-api-prod-eus2 \
  --resource-group rg-johnnybets-prod-eus2 \
  --revision $(az containerapp revision list --name ca-jbet-api-prod-eus2 --resource-group rg-johnnybets-prod-eus2 --query "[0].name" -o tsv)

# Check GitHub Actions
gh run list --repo dustinpitcher/johnnybets --limit 5
gh run view <run-id> --log-failed
```
