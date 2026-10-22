# Twin CubeSat Ground Station — Python backend

Runnable backend for **SAT-A** and **SAT-B**, aligned with the uploaded reconstructed Next.js frontend's GraphQL operation names and field casing.

## Includes

- FastAPI HTTP server and Strawberry GraphQL at `http://localhost:8000/graphql` (queries, mutations, WebSocket subscriptions).
- Separate InfluxDB 2.7 stores for SAT-A and SAT-B; PostgreSQL for packet records, channel catalog, commands, and minute summaries.
- Binary telemetry decoding using configurable channel definitions, validation of hexadecimal payload lengths and data types, quality evaluation from per-field limits.
- Authenticated HTTP packet ingestion for an external F Prime GDS Python extension/adapter.
- Background worker for idempotent minute-summary synchronization into PostgreSQL.
- Command records and an optional outbound HTTP bridge; simulation mode never claims a command reached a satellite.
- Docker Compose, Alembic migrations, and tests.

## Run (Windows PowerShell / Docker Desktop)

1. Copy `.env.example` to `.env` and **replace every placeholder secret**. Tokens must match InfluxDB initialization values on the first run.
2. Run `docker compose up --build -d`.
3. Open `http://localhost:8000/health`, `http://localhost:8000/graphql`, and `http://localhost:8000/docs`.
4. Test ingestion from Windows PowerShell (with Python installed): `$env:INGEST_API_KEY="your-key"; python scripts/send_demo_packet.py`. The script calls the host-mapped port `localhost:8000`.
5. Configure frontend `.env.local`:

   ```env
   NEXT_PUBLIC_DATA_SOURCE=graphql
   NEXT_PUBLIC_GRAPHQL_HTTP_URL=http://localhost:8000/graphql
   NEXT_PUBLIC_GRAPHQL_WS_URL=ws://localhost:8000/graphql
   ```

   Restart Next.js. The frontend still has legacy-mode components; switching the flag does not automatically convert every UI widget.

## GraphQL examples

```graphql
query { telemetryCatalog(satelliteId: "SAT-A") { version satelliteId channels { id name telemetryId fields { key format unit } } } }
```

```graphql
mutation { createRawTelemetryPacket(input:{satelliteId:"SAT-A",telemetryId:"3",payload:"41BC000042280000"}) { recordId decoded { values } } }
```

```graphql
subscription { telemetryPoint(satelliteId:"SAT-A") { channelId field value timestamp quality } }
```

## Important boundaries and integration details

- The three default telemetry IDs (1 LED, 2 IMU, 3 Environment) are **illustrative**, not an authoritative flight dictionary. The actual satellite channel IDs, endianness, CRC/framing, and byte layouts must be loaded from the mission's `TopologyDictionary.json` / F Prime definitions before flight use. **Do not send unvalidated RF frames directly to `/ingest/packet`**; the external GDS adapter must verify framing and CRC before forwarding a decoded payload.
- `/ingest/packet` and `/ingest/batch` require the `X-API-Key` header. The GraphQL endpoint is intended for a trusted local development network only; **authentication, authorization and command approval are not implemented**. Do not expose it publicly or connect it to a real transmitter without adding those controls.
- `COMMAND_SIMULATION=true` (default) stores commands as QUEUED only. To use a command bridge, set `COMMAND_SIMULATION=false`, `GDS_BRIDGE_URL` and `GDS_BRIDGE_TOKEN`. A 2xx from the bridge yields SENT, **not spacecraft acknowledgement**.
- GraphQL subscriptions use an **in-process event bus**; this works with a single API worker. Use Redis/NATS/Kafka to distribute events across workers/instances.
- InfluxDB writes and PostgreSQL commits are not distributed transactions. Production systems should use an outbox/queue and retries for guaranteed delivery. Minute summaries use idempotent upserts and per-satellite checkpoints, but backfill/retention policy must be configured for the mission.
- Updating/deleting raw packet records does **not** remove immutable time-series points from InfluxDB. Packet mutations are for test workflows, not audit-grade flight data modification.
- Database endpoints are private to Compose, except InfluxDB UIs bound to localhost. Do not publish credentials, `.env`, or local database volumes.
- For production use add TLS, user roles, authorization on GraphQL operations, command safety interlocks, durable event streaming, observability, backup/restore, and integration tests against the actual F Prime extension.

## F Prime integration contract

The GDS-side adapter sends HTTP `POST /ingest/packet` with header `X-API-Key` and JSON:

```json
{"satellite_id":"SAT-A","telemetry_id":"3","payload":"41BC000042280000","timestamp":"2026-10-22T09:00:00Z"}
```

The payload is **field bytes only**, not an entire RF frame. `timestamp` is optional. The backend routes SAT-A to InfluxDB A and SAT-B to InfluxDB B, and publishes in-process GraphQL subscription events.

The command bridge accepts `POST` with `{satellite_id,command_hex,command_id}` and bearer authorization. Adapt this HTTP bridge to the actual F Prime command API; do not assume an existing F Prime HTTP endpoint.

## Local tests

```sh
python -m pip install -r requirements.txt
pytest -q
```

## Repository layout

`app/main.py` REST ingest + startup, `app/graphql.py` schema, `app/service.py` processing and command bridge, `app/decoder.py` binary decoder, `app/influx.py` time-series storage, `app/models.py` PostgreSQL entities, `app/sync.py` summary worker, `migrations/` schema migrations.
