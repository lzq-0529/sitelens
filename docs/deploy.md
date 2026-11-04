# Deploy SiteLens

This is a private console. Put it behind HTTPS. Do not expose `/api/admin` to the public internet without that.

## Environment

| Variable | Purpose |
| --- | --- |
| `SITELENS_ENV=production` | Reject open collect (no token) |
| `SITELENS_SECRET_KEY` | Cookie signing; persist it |
| `SITELENS_COLLECT_TOKEN` | Tracker `data-token` / `X-Sitelens-Token` |
| `SITELENS_GEO_TOKEN` | GEO agent |
| `SITELENS_CRON_TOKEN` | `/api/cron/tick` |
| `SITELENS_CORS_ORIGINS` | Extra origins, comma-separated. Store hosts also come from settings. |
| `SITELENS_COOKIE_SECURE=1` | HTTPS-only session cookie |
| `SITELENS_DATA_DIR=/data` | SQLite + tokens |
| `SITELENS_DATABASE_URL` | Optional Postgres later |

CORS is **not** `*`. Browser collect only works from `cn_hosts` / `intl_hosts` / `domains` plus `SITELENS_CORS_ORIGINS`.

## Docker

```bash
docker compose up -d --build
```

Data lives in the `sitelens-data` volume. Create an owner before sharing the URL.

## Caddy (recommended)

```caddy
sitelens.yourdomain.com {
  encode gzip
  reverse_proxy sitelens:8788
}
```

## nginx

```nginx
server {
  listen 443 ssl;
  server_name sitelens.yourdomain.com;
  client_max_body_size 1m;

  location / {
    proxy_pass http://127.0.0.1:8788;
    proxy_set_header Host $host;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header X-Forwarded-Proto $scheme;
  }
}
```

Set `SITELENS_COOKIE_SECURE=1` when TLS terminates here.

## Cron

Hourly digest / due GEO reminder:

```
5 * * * * curl -fsS -X POST https://sitelens.yourdomain.com/api/cron/tick -H "x-cron-token: $SITELENS_CRON_TOKEN"
```

Weekly GEO agent (needs `SITELENS_LLM_URL`):

```
0 8 * * 1 python -m sitelens.manage geo-agent --base-url https://sitelens.yourdomain.com
```

Compose includes a `tick` sidecar that curls the same endpoint.
