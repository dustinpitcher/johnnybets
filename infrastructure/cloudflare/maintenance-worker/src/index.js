/**
 * JohnnyBets Maintenance Page Worker
 * 
 * Intercepts all requests and shows a maintenance page when enabled.
 * 
 * Activation methods:
 * 1. Set MAINTENANCE_MODE env var to "true" in wrangler.toml
 * 2. Use wrangler secret: wrangler secret put MAINTENANCE_MODE (enter "true")
 * 3. Quick toggle via Cloudflare dashboard > Workers > Settings > Variables
 */

export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    
    // Check if maintenance mode is enabled
    const maintenanceMode = env.MAINTENANCE_MODE === 'true';
    
    if (!maintenanceMode) {
      // Pass through to origin
      return fetch(request);
    }
    
    // Check for allowed IPs (bypass maintenance)
    const clientIP = request.headers.get('CF-Connecting-IP');
    const allowedIPs = (env.ALLOWED_IPS || '').split(',').map(ip => ip.trim()).filter(Boolean);
    
    if (allowedIPs.includes(clientIP)) {
      return fetch(request);
    }
    
    // Check for allowed paths (bypass maintenance)
    const allowedPaths = (env.ALLOWED_PATHS || '').split(',').map(p => p.trim()).filter(Boolean);
    
    for (const path of allowedPaths) {
      if (url.pathname.startsWith(path)) {
        return fetch(request);
      }
    }
    
    // Return maintenance page
    const html = generateMaintenancePage(env);
    
    return new Response(html, {
      status: 503,
      headers: {
        'Content-Type': 'text/html;charset=UTF-8',
        'Cache-Control': 'no-store, no-cache, must-revalidate',
        'Retry-After': '3600',
      },
    });
  },
};

function generateMaintenancePage(env) {
  const estimatedTime = env.ESTIMATED_TIME || 'shortly';
  const contactEmail = env.CONTACT_EMAIL || 'support@johnnybets.ai';
  
  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="robots" content="noindex, nofollow">
  <title>Maintenance | JohnnyBets</title>
  <style>
    * {
      margin: 0;
      padding: 0;
      box-sizing: border-box;
    }
    
    body {
      min-height: 100vh;
      display: flex;
      align-items: center;
      justify-content: center;
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
      background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
      color: #e2e8f0;
      padding: 20px;
    }
    
    .container {
      max-width: 600px;
      text-align: center;
      animation: fadeIn 0.6s ease-out;
    }
    
    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translateY(20px);
      }
      to {
        opacity: 1;
        transform: translateY(0);
      }
    }
    
    .logo {
      font-size: 3rem;
      font-weight: 800;
      background: linear-gradient(135deg, #22c55e 0%, #10b981 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
      background-clip: text;
      margin-bottom: 2rem;
      letter-spacing: -0.02em;
    }
    
    .icon {
      width: 80px;
      height: 80px;
      margin: 0 auto 2rem;
      background: linear-gradient(135deg, #22c55e 0%, #10b981 100%);
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      animation: pulse 2s ease-in-out infinite;
    }
    
    @keyframes pulse {
      0%, 100% {
        transform: scale(1);
        box-shadow: 0 0 0 0 rgba(34, 197, 94, 0.4);
      }
      50% {
        transform: scale(1.05);
        box-shadow: 0 0 0 20px rgba(34, 197, 94, 0);
      }
    }
    
    .icon svg {
      width: 40px;
      height: 40px;
      fill: #0f172a;
    }
    
    h1 {
      font-size: 2rem;
      font-weight: 700;
      margin-bottom: 1rem;
      color: #f8fafc;
    }
    
    .subtitle {
      font-size: 1.125rem;
      color: #94a3b8;
      margin-bottom: 2rem;
      line-height: 1.6;
    }
    
    .status-card {
      background: rgba(30, 41, 59, 0.5);
      border: 1px solid rgba(148, 163, 184, 0.1);
      border-radius: 12px;
      padding: 1.5rem;
      margin-bottom: 2rem;
      backdrop-filter: blur(10px);
    }
    
    .status-row {
      display: flex;
      justify-content: space-between;
      align-items: center;
      padding: 0.75rem 0;
      border-bottom: 1px solid rgba(148, 163, 184, 0.1);
    }
    
    .status-row:last-child {
      border-bottom: none;
    }
    
    .status-label {
      color: #94a3b8;
      font-size: 0.875rem;
    }
    
    .status-value {
      font-weight: 600;
      color: #f8fafc;
    }
    
    .status-value.active {
      color: #fbbf24;
    }
    
    .contact {
      color: #64748b;
      font-size: 0.875rem;
    }
    
    .contact a {
      color: #22c55e;
      text-decoration: none;
      transition: color 0.2s;
    }
    
    .contact a:hover {
      color: #4ade80;
      text-decoration: underline;
    }
    
    .refresh-hint {
      margin-top: 2rem;
      color: #475569;
      font-size: 0.75rem;
    }
  </style>
</head>
<body>
  <div class="container">
    <div class="logo">JohnnyBets</div>
    
    <div class="icon">
      <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24">
        <path d="M12 6V4m0 2a2 2 0 100 4m0-4a2 2 0 110 4m-6 8a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4m6 6v10m6-2a2 2 0 100-4m0 4a2 2 0 110-4m0 4v2m0-6V4"/>
      </svg>
    </div>
    
    <h1>We'll Be Right Back</h1>
    
    <p class="subtitle">
      We're performing scheduled maintenance to improve your experience. 
      We'll be back online ${estimatedTime}.
    </p>
    
    <div class="status-card">
      <div class="status-row">
        <span class="status-label">Status</span>
        <span class="status-value active">Maintenance in Progress</span>
      </div>
      <div class="status-row">
        <span class="status-label">Expected Duration</span>
        <span class="status-value">${estimatedTime}</span>
      </div>
    </div>
    
    <p class="contact">
      Need immediate assistance? <a href="mailto:${contactEmail}">${contactEmail}</a>
    </p>
    
    <p class="refresh-hint">
      This page will automatically refresh when we're back online.
    </p>
  </div>
  
  <script>
    // Auto-refresh every 30 seconds to check if maintenance is over
    setTimeout(() => {
      window.location.reload();
    }, 30000);
  </script>
</body>
</html>`;
}
