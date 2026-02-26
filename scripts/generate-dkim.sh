#!/usr/bin/env bash
# generate-dkim.sh — Generate DKIM key pair and print DNS records
# Usage: bash scripts/generate-dkim.sh example.com

set -euo pipefail

DOMAIN="${1:-}"
SELECTOR="${2:-default}"
KEY_DIR="mailserver/config/opendkim/keys/${DOMAIN}"

if [[ -z "$DOMAIN" ]]; then
    echo "Usage: $0 <domain> [selector]"
    echo "  domain   : e.g. example.com"
    echo "  selector : DKIM selector (default: 'default')"
    exit 1
fi

# ─── Create key directory ───
mkdir -p "$KEY_DIR"

PRIVKEY="${KEY_DIR}/${SELECTOR}.private"
PUBKEY="${KEY_DIR}/${SELECTOR}.txt"

if [[ -f "$PRIVKEY" ]]; then
    echo "[DKIM] Private key already exists: $PRIVKEY"
    echo "[DKIM] To regenerate, delete it first and re-run."
else
    echo "[DKIM] Generating 2048-bit RSA key pair..."
    openssl genrsa -out "$PRIVKEY" 2048 2>/dev/null
    chmod 600 "$PRIVKEY"
    echo "[DKIM] Private key saved: $PRIVKEY"
fi

# Extract public key (strip header/footer, join lines)
PUBKEY_DATA=$(openssl rsa -in "$PRIVKEY" -pubout 2>/dev/null \
    | grep -v '^-' | tr -d '\n')

# Save public key TXT record to file
cat > "$PUBKEY" <<EOF
${SELECTOR}._domainkey.${DOMAIN}. IN TXT "v=DKIM1; k=rsa; p=${PUBKEY_DATA}"
EOF
echo "[DKIM] Public key record saved: $PUBKEY"

echo ""
echo "================================================================"
echo "  DNS Records for ${DOMAIN}"
echo "================================================================"
echo ""
echo "── 1. MX Record ──"
echo "${DOMAIN}.  IN  MX  10  mail.${DOMAIN}."
echo ""
echo "── 2. SPF (TXT) ──"
echo "${DOMAIN}.  IN  TXT  \"v=spf1 mx a:mail.${DOMAIN} ~all\""
echo ""
echo "── 3. DKIM (TXT) ──"
echo "${SELECTOR}._domainkey.${DOMAIN}.  IN  TXT  \"v=DKIM1; k=rsa; p=${PUBKEY_DATA}\""
echo ""
echo "── 4. DMARC (TXT) ──"
echo "_dmarc.${DOMAIN}.  IN  TXT  \"v=DMARC1; p=quarantine; rua=mailto:postmaster@${DOMAIN}\""
echo ""
echo "── 5. Reverse DNS (PTR) ──"
echo "Set PTR record for your server IP → mail.${DOMAIN}"
echo ""
echo "================================================================"
echo "Add the above records to your DNS provider."
echo "After propagation, verify with: dig TXT ${SELECTOR}._domainkey.${DOMAIN}"
echo "================================================================"
