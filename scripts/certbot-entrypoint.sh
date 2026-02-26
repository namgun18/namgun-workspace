#!/bin/sh
set -e

# ── 도메인 인자 구성 ──
DOMAIN_ARGS=""
for d in $(echo "$ACME_DOMAINS" | tr ',' ' '); do
  DOMAIN_ARGS="$DOMAIN_ARGS -d $d"
done

if [ -z "$DOMAIN_ARGS" ]; then
  echo "[certbot] ACME_DOMAINS not set, exiting"
  exit 1
fi

# ── 초기 발급 (인증서가 없을 때) ──
NEED_ISSUE=true
for d in $(echo "$ACME_DOMAINS" | tr ',' ' '); do
  if [ -d "/etc/letsencrypt/live/$d" ]; then
    NEED_ISSUE=false
    break
  fi
done

if [ "$NEED_ISSUE" = true ]; then
  echo "[certbot] No existing certificate found — requesting initial issuance"
  if [ "$ACME_MODE" = "webroot" ]; then
    certbot certonly --webroot -w /var/www/certbot \
      --email "$ACME_EMAIL" --agree-tos --no-eff-email \
      $DOMAIN_ARGS
  else
    certbot certonly --standalone \
      --email "$ACME_EMAIL" --agree-tos --no-eff-email \
      $DOMAIN_ARGS
  fi
fi

# ── 자동 갱신 루프 (12시간 간격) ──
echo "[certbot] Starting renewal loop (every 12h)"
trap exit TERM
while :; do
  if [ "$ACME_MODE" = "webroot" ]; then
    certbot renew --webroot -w /var/www/certbot --quiet
  else
    certbot renew --standalone --quiet
  fi
  sleep 12h & wait $!
done
