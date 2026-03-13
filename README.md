# pretix-voucher-statistics

A pretix plugin that adds detailed statistics and analytics for vouchers.

## Features

### Per-voucher statistics (event level)
- List of all vouchers in an event with ticket counts, sortable by code, tag, or count
- Voucher detail page with two tabs:
  - **Orders & Attendees**: paginated table of every ticket ordered via the voucher — customer email, invoice address (name, company, street, ZIP, city, country), attendee name/email, ticket type, order date and status; columns are sortable
  - **Statistics**: timeline chart (daily + cumulative tickets) and a stacked comparison chart (this voucher vs. other vouchers vs. no voucher)

### Organizer-level statistics
Accessible under the organizer navigation:
- Select any combination of events
- **Cumulative tickets over time** – overlaid line chart per event
- **Ticket ramp-up** – normalized chart with x-axis = days before event start (−30 to 0), so you can directly compare how different events sold over their lead-up period
- **Top vouchers leaderboard** – per event, top 10 vouchers by ticket count with percentage bars

> Cancelled and refunded orders are excluded everywhere (only paid + pending orders are counted).

---

## Local development with Docker Compose

### Prerequisites
- Docker >= 24 and Docker Compose >= 2
- No other service running on port 8000

### 1. Clone and start

```bash
git clone https://github.com/your-org/pretix-voucher-statistics.git
cd pretix-voucher-statistics

# Start all services (first run builds the image – takes ~2 min)
docker compose up --build
```

The web UI is available at **http://localhost:8000/control/** once the container prints `Listening on...`.

### 2. Create a superuser

```bash
docker compose exec pretix pretix shell -c "
from django.contrib.auth import get_user_model
User = get_user_model()
User.objects.create_superuser('admin@example.com', 'admin@example.com', 'admin')
"
```

Then log in at http://localhost:8000/control/ with `admin@example.com` / `admin`.

### 3. Enable the plugin for an event

1. Create an organizer and an event in the pretix UI.
2. Go to **Event Settings -> Plugins** and enable **Voucher Statistics**.
3. Navigate to **Vouchers** in the event sidebar — the **Voucher Statistics** link appears below.

The organizer-level view is always visible in the organizer sidebar (no per-event activation needed).

### 4. Live code editing

Python changes inside `pretix_voucher_statistics/` are reflected after a container restart:

```bash
docker compose restart pretix
```

Template and static file changes take effect immediately (no restart needed for templates in dev mode).

### 5. Stopping and cleaning up

```bash
# Stop without deleting data
docker compose down

# Stop and delete all volumes (wipes the database)
docker compose down -v
```

---

## Installation (production)

```bash
pip install pretix-voucher-statistics
```

Add `pretix_voucher_statistics` to the `plugins` list in `pretix.cfg`, then run:

```bash
pretix migrate
pretix collectstatic
```

Restart the pretix web and worker processes. Enable the plugin per-event via **Event Settings -> Plugins**.

---

## Compatibility

- pretix >= 2026.1.1
- Python >= 3.9
- PostgreSQL (Redis for caching/Celery)

---

## License

Apache Software License 2.0
