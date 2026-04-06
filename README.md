# ChargeRelay

**Self-hosted OCPP 1.6 charging station management — open source, privacy-first, Docker-ready.**

ChargeRelay connects directly to your EV charging station via the open OCPP 1.6 protocol and gives you a clean web interface to monitor live sessions, track energy consumption per vehicle, and export reports — without sending your data to any cloud.

---

## Why ChargeRelay?

Most home and fleet charging stations ship with a vendor cloud app that locks your data behind a proprietary account. ChargeRelay runs entirely on your own server:

- **Full data ownership** — every charge session is stored in your own PostgreSQL database
- **No cloud dependency** — works offline on your local network
- **Vendor-agnostic** — any OCPP 1.6 compliant charger connects out of the box (tested with ABL, and others)
- **RFID-aware** — automatically identifies the charging vehicle by its RFID card, even when the charger uses a proxy/dummy tag in the transaction (e.g. ABL)
- **Fleet-ready** — manage multiple vehicles and chargers from one dashboard
- **Privacy-first** — optional UI password gate, no telemetry, no external requests

---

## Features

### Live Dashboard
- Real-time view of every active charging session
- Metrics: energy charged, power, current, voltage, state of charge (SoC), runtime
- Automatic vehicle identification via RFID tag
- Manual vehicle assignment directly from the live card

### Session History
- Paginated log of all completed and active sessions
- Shows vehicle, charge point, connector, start/end time, energy (kWh)
- Edit vehicle assignment after the fact

### Vehicle Management
- Register vehicles with name, photo and RFID tag
- Vehicles are automatically matched to sessions when their RFID card is presented
- Supports chargers that authorize with the real RFID but start the transaction with a dummy tag (common with ABL)

### Reports & Exports
- Group vehicles into named reports
- **CSV download** — choose a date range and individual vehicles, download immediately
- **Automated email delivery** — send CSV reports daily, weekly, monthly or yearly via SMTP
- **OCPP relay** — transparently forward all OCPP frames to a secondary backend (e.g. a utility provider's system)

### Internationalisation
- Full German 🇩🇪 and English 🇬🇧 UI
- Language persisted per browser
- CSV column headers match the selected language

### Infrastructure
- Single `docker compose up` deployment
- Built-in PostgreSQL container or plug in your own external database
- Optional UI password protection
- Responsive design — works on phone, tablet and desktop

---

## Tech Stack

| Layer | Technology |
|---|---|
| OCPP Server | Python 3.12 · asyncio · websockets · ocpp |
| REST API | FastAPI · psycopg2 |
| Frontend | Nuxt 3 · Vue 3 |
| Database | PostgreSQL 16 |
| Deployment | Docker · Docker Compose |

---

## Quick Start

### Prerequisites

- [Docker](https://docs.docker.com/get-docker/) and Docker Compose v2
- A charge point that speaks **OCPP 1.6 JSON** (WebSocket)

### 1 — Clone & configure

```bash
git clone https://github.com/your-org/chargerelay.git
cd chargerelay
cp .env.example .env
```

Open `.env` and set at minimum a secure database password:

```env
DB_PASSWORD=your-secure-password
```

The UI password (`UI_PASSWORD`) is **optional** — leave it empty and no login screen is shown. Useful for a private home network where you don't need authentication.

See the [full .env reference](#env-reference) below for all options.

### 2 — Start

```bash
make up
```

That's it. `make up` runs `docker compose up --build -d` under the hood. Other available commands:

| Command | Description |
|---|---|
| `make up` | Build images and start all containers |
| `make down` | Stop and remove all containers |
| `make logs` | Follow live logs for all services |
| `make build` | Rebuild images without starting |
| `make restart` | Restart the OCPP server only |
| `make test` | Run the test client against the OCPP server |

Or use Docker Compose directly:

```bash
# With the built-in Postgres container
COMPOSE_PROFILES=local-db docker compose up -d
```

The services will be available at:

| Service | Default address |
|---|---|
| Frontend (Web UI) | `http://your-server:3000` |
| OCPP WebSocket | `ws://your-server:9000` |
| REST API | `http://your-server:8000` |

> **Ports**: `3000` (frontend), `8000` (API) and `9000` (OCPP WebSocket) are exposed by default. When using a reverse proxy (nginx, Caddy, Traefik) remove the `ports:` entries from `docker-compose.yml` and let the proxy route traffic internally.

---

## Deployment Options

### Standard server (any Linux host)

Uses the built-in `chargerelay` bridge network. No additional tooling required.

```bash
cp .env.example .env
# edit .env — set DB_PASSWORD and COMPOSE_PROFILES=local-db
docker compose up -d
```

### Dokploy

ChargeRelay includes a dedicated Dokploy override that attaches all containers to the shared `dokploy-network`. In Dokploy's compose configuration, add the override file:

```
docker-compose.yml + docker-compose.dokploy.yml
```

Or in the Dokploy UI, set **Compose File** to:

```
docker-compose.yml
```

and **Additional Compose Files** to:

```
docker-compose.dokploy.yml
```

### Local development

No extra files needed — just run `docker compose up -d`. Ports are already exposed in `docker-compose.yml`.

### 3 — Connect your charge point

Point your charger's OCPP backend URL to:

```
ws://your-server:9000/ocpp/<station-id>
```

Replace `<station-id>` with any identifier you like (e.g. `home-wallbox`). The station registers itself automatically on first boot.

---

## .env Reference

Copy `.env.example` to `.env` and adjust the values for your setup.

```env
# ── Database ──────────────────────────────────────────────────────────────────

# "postgres" = use the built-in Docker container (requires COMPOSE_PROFILES=local-db)
# Set to a hostname/IP to use your own external PostgreSQL server instead.
DB_HOST=postgres
DB_PORT=5432
DB_NAME=ocpp
DB_USER=ocpp
DB_PASSWORD=change-me          # ← set a strong password

# ── Docker Compose profiles ───────────────────────────────────────────────────

# Include "local-db" to start the built-in Postgres container.
# Leave empty when using an external database.
COMPOSE_PROFILES=local-db

# ── UI password gate ──────────────────────────────────────────────────────────

# Protects the web interface with a password prompt.
# Leave empty to disable the login screen entirely (e.g. on a private LAN).
UI_PASSWORD=

# ── Default UI language ───────────────────────────────────────────────────────

# "de" (German) or "en" (English). Users can switch language in the UI.
DEFAULT_LOCALE=de

# ── SMTP — automated email reports ───────────────────────────────────────────

# Required only if you configure email deliveries in the Reports section.
SMTP_HOST=smtp.example.com
SMTP_PORT=587
SMTP_USER=user@example.com
SMTP_PASSWORD=change-me
SMTP_FROM=ocpp-reports@example.com
```

---

## Using an External Database

By default ChargeRelay starts its own PostgreSQL container. To use an existing database instead:

1. Set `DB_HOST` to your database server's hostname or IP
2. Set `COMPOSE_PROFILES=` (empty — no built-in Postgres)
3. Create the database and user on your server:

```sql
CREATE DATABASE ocpp;
CREATE USER ocpp WITH PASSWORD 'your-password';
GRANT ALL PRIVILEGES ON DATABASE ocpp TO ocpp;
```

ChargeRelay creates all tables automatically on startup.

---

## Reports & Email Delivery

### Manual CSV Download

1. Open the **Reports** tab
2. Click **+ New Report**, give it a name and assign vehicles
3. On the report card, click the **CSV** button
4. Choose a date range and which vehicles to include
5. Click **Download**

The CSV uses a semicolon delimiter and UTF-8 BOM encoding for direct Excel compatibility.

### Automated Email Reports

1. Create a report and add an **Email** delivery
2. Set the recipient address and interval (daily / weekly / monthly / yearly)
3. Configure your SMTP credentials in `.env`

ChargeRelay checks every 5 minutes whether a delivery is due and sends the CSV as an email attachment automatically.

### OCPP Relay

Add an **OCPP Relay** delivery to transparently forward all OCPP frames from your charger to a secondary backend — useful when your utility requires access to your charger's data.

---

## Development Setup

```bash
# Backend (OCPP server)
cd backend
pip install -r requirements.txt
python main.py

# API
cd api
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Frontend
cd frontend
npm install
npm run dev
```

The Nuxt dev server proxies `/api` to `localhost:8000` automatically.

---

## Architecture

```
Charge Point (OCPP 1.6)
        │  WebSocket ws://…:9000
        ▼
┌──────────────────┐
│   OCPP Server    │  Python · asyncio · websockets
│  (backend/)      │  • Handles BootNotification, Authorize,
│                  │    StartTransaction, StopTransaction,
│                  │    MeterValues, StatusNotification
│                  │  • Persists sessions to PostgreSQL
│                  │  • Forwards frames to relay targets
└────────┬─────────┘
         │ PostgreSQL
         ▼
┌──────────────────┐        ┌──────────────────┐
│   REST API       │◄───────│    Frontend      │
│  (api/)          │  HTTP  │  (frontend/)     │
│  FastAPI         │        │  Nuxt 3 · Vue 3  │
└──────────────────┘        └──────────────────┘
```

---

## License

MIT — see [LICENSE](LICENSE) for details.

---

*Built by Theo Bauer.*
