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

### General (any pretix installation)

The plugin is installed into the same Python environment that runs pretix.

Install directly from GitHub:

```bash
pip install git+https://github.com/vlietz/pretix-voucher-statistics.git
```

Or build and install inside the container (recommended when host and server architectures differ):

Clone the repo on the server, copy the source into the running container, and let pip build and install it there. This ensures the wheel is compiled for the correct OS and CPU architecture (important when your dev machine is macOS/ARM and the server is Linux/x86).

```bash
# 1. SSH into your server
ssh yourserver

# 2. Clone the repo on the server
git clone https://github.com/vlietz/pretix-voucher-statistics.git /opt/pretix-voucher-statistics

# 3. Copy the source into the running pretix container
docker compose cp /opt/pretix-voucher-statistics pretix:/tmp/plugin

# 4. Build and install inside the container (run as root so pip can write build files)
docker compose exec --user root pretix pip3 install /tmp/plugin

# 5. Restart pretix to pick up the new package
docker compose restart pretix
```

After installing, restart the pretix web workers so the new package is picked up:

```bash
# Typical systemd setup
systemctl restart pretix-web

# Or supervisord
supervisorctl restart pretixweb
```

Then enable the plugin per event in the pretix control panel: **Settings -> Plugins -> Voucher Statistics -> Enable**

### Updating to a newer version

```bash
# Pull the latest source on the server
cd /opt/pretix-voucher-statistics && git pull

# Remove the old copy inside the container first (otherwise cp copies into a subdirectory)
docker compose exec --user root pretix rm -rf /tmp/plugin

# Copy updated source into the container and reinstall
docker compose cp /opt/pretix-voucher-statistics pretix:/tmp/plugin
docker compose exec --user root pretix pip3 install --upgrade --no-cache-dir /tmp/plugin
docker compose restart pretix
```

Or if installed directly via pip:

```bash
pip install --upgrade git+https://github.com/vlietz/pretix-voucher-statistics.git
systemctl restart pretix-web
```

---

## Compatibility

- pretix >= 2026.1.1
- Python >= 3.9
- PostgreSQL (Redis for caching/Celery)

---

## License

Apache Software License 2.0
