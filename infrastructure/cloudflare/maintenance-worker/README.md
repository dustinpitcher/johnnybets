# JohnnyBets Maintenance Page Worker

A Cloudflare Worker that displays a maintenance page when activated. Can be quickly toggled on/off without redeploying the main application.

## Setup

1. Install dependencies:
   ```bash
   cd infrastructure/cloudflare/maintenance-worker
   npm install
   ```

2. Authenticate with Cloudflare (if not already):
   ```bash
   npx wrangler login
   ```

3. Configure routes in `wrangler.toml`:
   ```toml
   routes = [
     { pattern = "johnnybets.ai/*", zone_name = "johnnybets.ai" },
     { pattern = "www.johnnybets.ai/*", zone_name = "johnnybets.ai" }
   ]
   ```

4. Deploy the worker:
   ```bash
   npm run deploy
   ```

## Activating Maintenance Mode

### Option 1: Cloudflare Dashboard (Fastest)
1. Go to Cloudflare Dashboard > Workers & Pages
2. Select `johnnybets-maintenance`
3. Go to Settings > Variables
4. Edit `MAINTENANCE_MODE` and set to `true`
5. Save

### Option 2: Wrangler CLI
```bash
# Enable maintenance mode
echo "true" | npx wrangler secret put MAINTENANCE_MODE

# Disable maintenance mode
echo "false" | npx wrangler secret put MAINTENANCE_MODE
```

### Option 3: Redeploy with Updated Config
1. Edit `wrangler.toml` and set `MAINTENANCE_MODE = "true"`
2. Run `npm run deploy`

## Deactivating Maintenance Mode

Same as above, but set `MAINTENANCE_MODE` to `false`.

## Configuration Options

| Variable | Description | Default |
|----------|-------------|---------|
| `MAINTENANCE_MODE` | Set to "true" to enable maintenance page | `"false"` |
| `ALLOWED_IPS` | Comma-separated IPs that bypass maintenance | `""` |
| `ALLOWED_PATHS` | Comma-separated paths that bypass maintenance | `""` |
| `ESTIMATED_TIME` | Time estimate shown to users | `"shortly"` |
| `CONTACT_EMAIL` | Contact email for support | `"support@johnnybets.ai"` |

## Bypass Maintenance

### For Specific IPs
Set `ALLOWED_IPS` in wrangler.toml or as a secret:
```toml
ALLOWED_IPS = "203.0.113.50,198.51.100.25"
```

### For Specific Paths
Health checks, status endpoints, etc:
```toml
ALLOWED_PATHS = "/api/health,/api/status"
```

## Local Development

Test the worker locally:
```bash
npm run dev
```

Then visit http://localhost:8787

To test with maintenance mode enabled, temporarily set `MAINTENANCE_MODE = "true"` in `wrangler.toml`.

## Monitoring

View live logs from the deployed worker:
```bash
npm run tail
```

## Quick Reference

```bash
# Deploy
npm run deploy

# Enable maintenance (via secret)
echo "true" | npx wrangler secret put MAINTENANCE_MODE

# Disable maintenance (via secret)  
echo "false" | npx wrangler secret put MAINTENANCE_MODE

# View logs
npm run tail

# Local dev
npm run dev
```
