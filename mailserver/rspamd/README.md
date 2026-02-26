# Rspamd Configuration

Place custom Rspamd configuration files here.
They will be mounted to `/etc/rspamd/local.d/` in the container.

## Recommended modules:
- DKIM signing (`dkim_signing.conf`)
- SPF checking
- ARC signing
- Milter integration with Postfix
