# Postfix Configuration

Place custom Postfix configuration files here.
They will be mounted to `/etc/postfix/custom/` in the container.

## Required for production:
- TLS certificates (or use Let's Encrypt)
- DKIM signing (via Rspamd milter)
- Virtual mailbox maps (PostgreSQL query)

## Environment variables:
- `ALLOWED_SENDER_DOMAINS` — Your domain
- `HOSTNAME` — Mail server hostname (e.g., mail.example.com)
