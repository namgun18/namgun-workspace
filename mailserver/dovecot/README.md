# Dovecot Configuration

Place custom Dovecot configuration files here.
They will be mounted to `/etc/dovecot/conf.d/custom/` in the container.

## SQL auth (PostgreSQL):
Configure `auth-sql.conf.ext` to authenticate against the workspace `users` table:

```sql
driver = pgsql
connect = host=postgres dbname=workspace user=workspace password=...
default_pass_scheme = BLF-CRYPT
password_query = SELECT username, password_hash as password FROM users WHERE username='%u' AND is_active=true
```
