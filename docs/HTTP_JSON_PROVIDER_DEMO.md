# HTTP JSON Provider Demo

This demo shows the bounded read-only Generic HTTP JSON Provider v0 with a local mock feed. It does not require a real external API.

## What this proves

- A generated model-driven AgentForge app can sync read-only JSON records from an HTTP endpoint.
- The `http_json` provider is generic and not tied to GitHub.
- Provider sync reuses the existing importer pipeline for mapping, validation, relation-by-label behavior, reject-on-invalid commits, upsert/idempotency, and import-run history.
- Provider code does not write entity rows directly; the target import owns validation and upsert behavior.
- There is no OAuth, no write-back, no scheduled sync, no provider marketplace, and no live external service required for this demo.
- Default generated validation/tests use mocks, so `make validate` does not need a live URL, token, or network.

## Generate the app

From the AgentForge repo root:

```bash
agentforge generate domain-packs/http-json-vendor-feed/domain-pack.yaml --output .tmp/http-json-vendor-feed --force
cd .tmp/http-json-vendor-feed
make validate
```

The generated app includes a `Vendors` entity, a JSON import with `upsert_key: external_id`, and one read-only provider:

```text
external_vendor_feed -> vendor_feed_import -> vendor records
```

## Create a local mock JSON feed

In a terminal from the generated app root:

```bash
mkdir -p .tmp/mock-feed
cat > .tmp/mock-feed/vendors.json <<'JSON'
{
  "data": [
    {
      "external_id": "vendor-001",
      "name": "Northstar Payroll",
      "service_area": "Payroll",
      "risk_level": "high",
      "owner": "Maya",
      "source_url": "https://example.com/vendors/vendor-001"
    },
    {
      "external_id": "vendor-002",
      "name": "Atlas Email Gateway",
      "service_area": "Email",
      "risk_level": "medium",
      "owner": "Yuri",
      "source_url": "https://example.com/vendors/vendor-002"
    }
  ]
}
JSON
cd .tmp/mock-feed
python -m http.server 8899
```

The example pack uses `source.records_path: data`, so the provider extracts the `data` array.

## Configure provider environment

In the backend terminal, set the provider environment before starting the backend:

```bash
export EXTERNAL_VENDOR_FEED_URL=http://127.0.0.1:8899/vendors.json
export EXTERNAL_VENDOR_FEED_TOKEN=local-demo-token
```

For this example pack, `source.auth: bearer` and `env.token: EXTERNAL_VENDOR_FEED_TOKEN` are configured. The generated provider therefore treats both `EXTERNAL_VENDOR_FEED_URL` and `EXTERNAL_VENDOR_FEED_TOKEN` as required env vars. The token can be fake for the local `python -m http.server` mock; it is only added as an `Authorization: Bearer ...` request header.

Never commit `.env` or real token values. The Providers panel shows env var names and missing/configured status only; it does not show secret values.

## Run the generated app

Terminal 1, with the env vars above set:

```bash
make run-backend
```

Terminal 2:

```bash
make run-frontend
```

Open `http://localhost:5173`.

## Use the Providers panel

1. Click **Providers** in the sidebar.
2. Confirm the External Vendor Feed env status is configured/ready. If it is missing env vars, stop the backend, export the vars, and restart it.
3. Click **Preview**. Confirm two vendor records are previewed and would be created.
4. Click **Sync**.
5. Open **Vendors** and confirm the two records appear.
6. Click **Providers**, preview/sync again, and confirm records update/upsert instead of duplicating because `external_id` is the import upsert key.
7. Check the provider run history in the Providers panel. It should show provider/import runs with created/updated/error counts.

## Optional API smoke

With backend running:

```bash
curl http://127.0.0.1:8000/providers
curl -X POST http://127.0.0.1:8000/providers/external_vendor_feed/preview
curl -X POST http://127.0.0.1:8000/providers/external_vendor_feed/sync
curl -X POST http://127.0.0.1:8000/providers/external_vendor_feed/sync
curl http://127.0.0.1:8000/providers/runs
curl http://127.0.0.1:8000/vendor
```

On the first sync, expect two creates. On the second sync, expect updates rather than duplicate vendor rows.

## Troubleshooting

- **Missing `EXTERNAL_VENDOR_FEED_URL` or `EXTERNAL_VENDOR_FEED_TOKEN`**: `/providers` reports `configured: false` and lists missing env var names. Export both vars and restart the backend.
- **Local mock server not running**: preview/sync returns an HTTP JSON provider request failure. Restart `python -m http.server 8899` in `.tmp/mock-feed`.
- **Wrong port/path**: verify `http://127.0.0.1:8899/vendors.json` opens in a browser or with `curl`.
- **Invalid JSON**: the provider reports `HTTP JSON provider returned invalid JSON`. Recreate `vendors.json` and validate commas/braces.
- **Wrong `records_path`**: this pack expects `data`. If the response shape changes, update the Blueprint `source.records_path` before regenerating.
- **Records are not a list of objects**: extracted records must be a JSON array, and every item must be an object.
- **Enum validation error for `risk_level`**: allowed values are `low`, `medium`, and `high`; any other value is rejected by the importer.
- **Bearer token behavior**: this pack requires `EXTERNAL_VENDOR_FEED_TOKEN` because `auth: bearer` is configured. The local mock accepts any fake value.
- **Stale generated app/frontend build**: regenerate with `agentforge generate ... --force`, rerun `make validate`, and restart backend/frontend.
- **Sync appears to duplicate**: confirm each record has a stable `external_id`; the `vendor_feed_import` upserts by that field.

## Safety notes

- The provider is read-only and does not mutate external services.
- The generated app writes only to its local SQLite database through the importer commit path.
- Token values are env-only and are not shown in the UI.
- Never commit `.env`, real tokens, or private URLs.
- The local mock demo can be run with fake data only.
