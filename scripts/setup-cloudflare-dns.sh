#!/bin/bash
# Setup Cloudflare DNS for johnnybets.ai
# 
# Prerequisites:
# 1. Create an API token at https://dash.cloudflare.com/profile/api-tokens
#    with "Zone:DNS:Edit" permission for johnnybets.ai
# 2. Export your token: export CLOUDFLARE_API_TOKEN="your_token_here"

set -e

# Configuration
DOMAIN="johnnybets.ai"
STATIC_WEB_APP="proud-hill-0f5a2340f.6.azurestaticapps.net"
CONTAINER_APP="ca-jbet-api-prod-eus2.blueplant-0e5d4fc7.eastus2.azurecontainerapps.io"
VALIDATION_TOKEN="_y1synq43vsv2o46kn240701qz7cq6yb"

# Check for API token
if [ -z "$CLOUDFLARE_API_TOKEN" ]; then
    echo "Error: CLOUDFLARE_API_TOKEN environment variable not set"
    echo ""
    echo "Create an API token at https://dash.cloudflare.com/profile/api-tokens"
    echo "Required permissions: Zone:DNS:Edit for johnnybets.ai"
    echo ""
    echo "Then run: export CLOUDFLARE_API_TOKEN='your_token_here'"
    exit 1
fi

API_BASE="https://api.cloudflare.com/client/v4"

# Function to make API calls
cf_api() {
    local method=$1
    local endpoint=$2
    local data=$3
    
    if [ -n "$data" ]; then
        curl -s -X "$method" "$API_BASE$endpoint" \
            -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN" \
            -H "Content-Type: application/json" \
            -d "$data"
    else
        curl -s -X "$method" "$API_BASE$endpoint" \
            -H "Authorization: Bearer $CLOUDFLARE_API_TOKEN"
    fi
}

echo "🔍 Finding zone ID for $DOMAIN..."
ZONE_RESPONSE=$(cf_api GET "/zones?name=$DOMAIN")
ZONE_ID=$(echo "$ZONE_RESPONSE" | jq -r '.result[0].id')

if [ "$ZONE_ID" == "null" ] || [ -z "$ZONE_ID" ]; then
    echo "Error: Could not find zone for $DOMAIN"
    echo "Response: $ZONE_RESPONSE"
    exit 1
fi

echo "✅ Found zone ID: $ZONE_ID"

# Function to create or update DNS record
create_dns_record() {
    local type=$1
    local name=$2
    local content=$3
    local proxied=$4
    
    echo ""
    echo "📝 Creating $type record: $name -> $content"
    
    # Check if record exists
    local existing=$(cf_api GET "/zones/$ZONE_ID/dns_records?type=$type&name=$name.$DOMAIN")
    local record_id=$(echo "$existing" | jq -r '.result[0].id')
    
    local data="{\"type\":\"$type\",\"name\":\"$name\",\"content\":\"$content\",\"proxied\":$proxied,\"ttl\":1}"
    
    if [ "$record_id" != "null" ] && [ -n "$record_id" ]; then
        echo "   Record exists, updating..."
        local result=$(cf_api PUT "/zones/$ZONE_ID/dns_records/$record_id" "$data")
    else
        echo "   Creating new record..."
        local result=$(cf_api POST "/zones/$ZONE_ID/dns_records" "$data")
    fi
    
    local success=$(echo "$result" | jq -r '.success')
    if [ "$success" == "true" ]; then
        echo "   ✅ Success"
    else
        echo "   ❌ Failed: $(echo "$result" | jq -r '.errors')"
    fi
}

# Create DNS records
echo ""
echo "🌐 Setting up DNS records for $DOMAIN..."

# TXT record for Azure validation (apex)
echo ""
echo "📝 Creating TXT validation record..."
TXT_DATA="{\"type\":\"TXT\",\"name\":\"@\",\"content\":\"$VALIDATION_TOKEN\",\"ttl\":1}"
TXT_RESULT=$(cf_api POST "/zones/$ZONE_ID/dns_records" "$TXT_DATA")
TXT_SUCCESS=$(echo "$TXT_RESULT" | jq -r '.success')
if [ "$TXT_SUCCESS" == "true" ]; then
    echo "   ✅ TXT record created"
else
    # Check if it already exists
    echo "   Record may already exist, checking..."
fi

# CNAME for apex (@ -> Static Web App)
# Note: Cloudflare supports CNAME flattening at apex
echo ""
echo "📝 Creating CNAME for apex domain..."
APEX_DATA="{\"type\":\"CNAME\",\"name\":\"@\",\"content\":\"$STATIC_WEB_APP\",\"proxied\":true,\"ttl\":1}"
APEX_EXISTING=$(cf_api GET "/zones/$ZONE_ID/dns_records?type=CNAME&name=$DOMAIN")
APEX_ID=$(echo "$APEX_EXISTING" | jq -r '.result[0].id')
if [ "$APEX_ID" != "null" ] && [ -n "$APEX_ID" ]; then
    APEX_RESULT=$(cf_api PUT "/zones/$ZONE_ID/dns_records/$APEX_ID" "$APEX_DATA")
else
    APEX_RESULT=$(cf_api POST "/zones/$ZONE_ID/dns_records" "$APEX_DATA")
fi
echo "   $(echo "$APEX_RESULT" | jq -r 'if .success then "✅ Success" else "❌ " + (.errors | tostring) end')"

# CNAME for www
echo ""
echo "📝 Creating CNAME for www..."
WWW_DATA="{\"type\":\"CNAME\",\"name\":\"www\",\"content\":\"$STATIC_WEB_APP\",\"proxied\":true,\"ttl\":1}"
WWW_EXISTING=$(cf_api GET "/zones/$ZONE_ID/dns_records?type=CNAME&name=www.$DOMAIN")
WWW_ID=$(echo "$WWW_EXISTING" | jq -r '.result[0].id')
if [ "$WWW_ID" != "null" ] && [ -n "$WWW_ID" ]; then
    WWW_RESULT=$(cf_api PUT "/zones/$ZONE_ID/dns_records/$WWW_ID" "$WWW_DATA")
else
    WWW_RESULT=$(cf_api POST "/zones/$ZONE_ID/dns_records" "$WWW_DATA")
fi
echo "   $(echo "$WWW_RESULT" | jq -r 'if .success then "✅ Success" else "❌ " + (.errors | tostring) end')"

# CNAME for api
echo ""
echo "📝 Creating CNAME for api..."
API_DATA="{\"type\":\"CNAME\",\"name\":\"api\",\"content\":\"$CONTAINER_APP\",\"proxied\":true,\"ttl\":1}"
API_EXISTING=$(cf_api GET "/zones/$ZONE_ID/dns_records?type=CNAME&name=api.$DOMAIN")
API_ID=$(echo "$API_EXISTING" | jq -r '.result[0].id')
if [ "$API_ID" != "null" ] && [ -n "$API_ID" ]; then
    API_RESULT=$(cf_api PUT "/zones/$ZONE_ID/dns_records/$API_ID" "$API_DATA")
else
    API_RESULT=$(cf_api POST "/zones/$ZONE_ID/dns_records" "$API_DATA")
fi
echo "   $(echo "$API_RESULT" | jq -r 'if .success then "✅ Success" else "❌ " + (.errors | tostring) end')"

echo ""
echo "🎉 DNS configuration complete!"
echo ""
echo "Next steps:"
echo "1. Wait 1-2 minutes for DNS propagation"
echo "2. Run the Azure domain validation commands:"
echo ""
echo "   # Verify apex domain"
echo "   az staticwebapp hostname set \\"
echo "     --name swa-jbet-web-prod-eus2 \\"
echo "     --resource-group rg-johnnybets-prod-eus2 \\"
echo "     --hostname johnnybets.ai \\"
echo "     --validation-method dns-txt-token"
echo ""
echo "   # Add www subdomain"
echo "   az staticwebapp hostname set \\"
echo "     --name swa-jbet-web-prod-eus2 \\"
echo "     --resource-group rg-johnnybets-prod-eus2 \\"
echo "     --hostname www.johnnybets.ai"
echo ""
echo "   # Add api subdomain to Container App"
echo "   az containerapp hostname add \\"
echo "     --name ca-jbet-api-prod-eus2 \\"
echo "     --resource-group rg-johnnybets-prod-eus2 \\"
echo "     --hostname api.johnnybets.ai"
