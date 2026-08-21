# Seam(De)Stress

<div align="center">

### Order management & destressing for alterations shops

**Track clients. Plan the workload. Quote and invoice. All in one place.**

[🎯 What is it?](#-what-is-it) • [🚀 Quick Start](#-quick-start) • [✨ Features](#-features) • [📸 Screenshots](#-screenshots) • [⚙️ Configuration](#️-configuration) • [🧵 Tech Stack](#-tech-stack) • [🛠️ Development](#️-development) • [🌍 Translations](#-translations)

---

</div>

## 🎯 What is it?

Seam(De)Stress is a **self-hosted order-management tool for a seamstress or
alterations shop**. It replaces the paper ticket book and the mental math at
the counter: intake a garment in under a minute, see at a glance whether this
week is already overbooked, and hand the client a printable ticket with a QR
code they can use to check status from their phone — no account required.

**Perfect for:**
- ✂️ **Alterations & tailoring shops** juggling dozens of garments a week
- 🧵 **Solo seamstresses** who need the counter workflow to be fast, not fussy
- 📅 **Anyone drowning in due dates** — the workload calendar exists so nothing
  gets promised for a day that's already full

## 🚀 Quick Start

```bash
git clone <this-repo-url> seamdestress
cd seamdestress
cp env.example .env
# edit .env — at minimum set SECRET_KEY and the POSTGRES_*/ADMIN_* values
docker compose up -d
```

The app is now running at `http://localhost:5000`. Migrations run
automatically on startup. To create the initial admin user and load a
realistic demo dataset (clients, a service catalog, orders in every status,
one invoice):

```bash
docker compose exec app flask seed
```

Sign in with the `ADMIN_USERNAME` / `ADMIN_PASSWORD` you set in `.env`
(defaults to `admin` / `changeme123` — change this before exposing the app).

For local development with live reload instead of the production image:

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

## ✨ Features

- **Fast intake** — search or create a client, add garments, tap alterations
  from a searchable, most-used-first service catalog (or type a custom
  line), see the running total, upload garment photos from a phone, and
  print a ticket — all without leaving the order screen.
- **Service catalog** — admin-managed price list by category, with default
  price, VAT rate, and estimated work minutes per alteration; seeded with
  ~30 realistic Belgian alteration prices out of the box.
- **Inventory** — track materials (thread, zippers, buttons, fabric, ...)
  with quantity on hand, a low-stock indicator, and a full stock-movement
  audit log (received / consumed / adjusted). Pick a material on an order
  line just like a catalog service — stock is consumed automatically and
  the line flows through to invoicing with no extra steps.
- **Garments & photos** — each order holds one or more garments (type,
  color, brand, measurements) with EXIF-corrected, thumbnailed photos
  stored on a mounted volume.
- **Garment tickets & receipts** — a printable per-garment ticket (label-
  width or A4) with a QR code back to the staff order view, plus a
  separate client receipt with a QR code to the online tracking page.
- **Workload planning** — a weekly calendar that charges each order's
  estimated minutes against a configurable daily capacity, with an overdue
  panel, an express lane, and a workload preview right on the intake form
  so you never promise a day that's already full.
- **Dashboard** — today's pickups, due-soon and overdue counts, one-click
  status advances, and a recent-activity feed.
- **Client portal** — a tokenized, no-login tracking page per order: shop
  branding, a status timeline, a "ready for pickup" banner, itemized
  alterations (prices optional), and shop address/hours. Links are
  revocable and regenerable at any time.
- **Notifications** — a one-click "notify client" action emails the client
  when their order is ready, in their own language, with consent
  respected and every attempt logged — the app keeps working even if SMTP
  isn't configured yet.
- **Invoicing** — combine one or more orders into a sequentially-numbered
  (`2026-0001`) invoice, download a branded WeasyPrint PDF with a VAT
  breakdown, track draft/sent/paid/overdue status, see a monthly revenue
  overview, and export the invoice list to CSV. Invoicing is admin-only,
  matching a typical shop's separation between counter staff and the books.
- **Settings & branding** — shop name, address, phone, opening hours, logo,
  VAT number and IBAN, daily planning capacity, and whether the client
  portal shows prices — all editable from the app, no redeploy needed.
- **Search** — the topbar search box looks across client name/phone/email,
  order codes (and the client name on an order), and garment description/
  brand/color in one go.
- **Multilingual** — the client portal, printed documents, and the core
  staff shell (dashboard, sidebar, login, account page) are available in
  Dutch (default), French, and English, with documents rendered in the
  *client's* language regardless of which staff member is logged in.

*(Feature list tracks the original build spec; see [CLAUDE.md](CLAUDE.md)
for the milestone-by-milestone log of what shipped and the reasoning
behind each scope decision.)*

## 📸 Screenshots

_Coming soon — screenshots will be added here as the UI takes shape._

## ⚙️ Configuration

All configuration is via environment variables — copy `env.example` to `.env`
and adjust. Key variables:

| Variable | Default | Description |
|---|---|---|
| `SECRET_KEY` | _(none — required)_ | Flask session/CSRF signing key. Generate a long random string. |
| `SESSION_COOKIE_SECURE` | `true` | Set `false` only for local HTTP development. |
| `DATABASE_URL` | _(built from `POSTGRES_*`)_ | Full SQLAlchemy URL; overrides the `POSTGRES_*` vars if set. |
| `POSTGRES_DB` / `POSTGRES_USER` / `POSTGRES_PASSWORD` | `seamdestress` | Database credentials used by `docker-compose.yml`. |
| `UPLOAD_FOLDER` | `/data/uploads` | Mounted volume for garment photos and the shop logo. |
| `MAX_CONTENT_LENGTH_MB` | `15` | Upload size limit. |
| `DEFAULT_LOCALE` | `nl` | Default UI/document language: `nl`, `fr`, or `en`. Staff can change their own in **My account**; clients get their own `preferred_language` on documents and the portal. |
| `DEFAULT_TIMEZONE` | `Europe/Brussels` | Used for due dates and scheduling. |
| `DEFAULT_VAT_RATE` | `21` | Belgian standard rate; each catalog item can override it (e.g. 6% for repairs). |
| `LOGIN_RATE_LIMIT` | `10 per minute` | Login attempts allowed per IP. |
| `ADMIN_USERNAME` / `ADMIN_PASSWORD` / `ADMIN_EMAIL` / `ADMIN_FULL_NAME` | `admin` / `changeme123` / ... | Initial admin user created by `flask seed`. |
| `SMTP_HOST` / `SMTP_PORT` / `SMTP_USERNAME` / `SMTP_PASSWORD` / `SMTP_USE_TLS` / `SMTP_FROM_ADDRESS` | _(empty)_ | Outgoing mail for "your garment is ready" notifications. Leave `SMTP_HOST` empty to run without email — notify attempts are logged as failed instead of erroring. |

Shop branding (name, address, phone, opening hours, logo, VAT number, IBAN),
the daily planning capacity, and the client-portal price-visibility toggle
are configured from **Settings** in the app itself (admin-only), not
environment variables. See `env.example` for the complete list of env vars.

## 🧵 Tech Stack

- **Python 3.12, Flask, SQLAlchemy 2.x, Alembic** — backend & migrations
- **PostgreSQL** — database (SQLite supported for local dev only)
- **Bootstrap 5** (vendored, no CDN) + a little vanilla JS — frontend, no
  SPA framework
- **Flask-Login, Flask-WTF, Flask-Limiter, Argon2** — auth & session security
- **Flask-Babel** — Dutch/French/English translations
- **WeasyPrint** — invoice PDFs; garment tickets and the client receipt are
  print-styled HTML instead (no PDF dependency needed for those)
- **Pillow, qrcode** — photo thumbnailing and QR code generation
- **Gunicorn** behind Docker — production serving

## 🛠️ Development

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
cp env.example .env   # and set DB_DRIVER=sqlite for a dependency-free local DB
flask db upgrade
flask seed
flask run --debug
```

Run the test suite and linter:

```bash
pytest -q                              # add --cov=app --cov-report=term-missing for coverage
ruff check .
```

See [CLAUDE.md](CLAUDE.md) for architecture decisions and conventions.

## 🌍 Translations

UI strings live in `app/translations/{nl,fr}/LC_MESSAGES/messages.po`
(English is the source text itself — no catalog needed). After changing a
translatable string in a template or route:

```bash
pybabel extract -F babel.cfg -k lazy_gettext -k _l -o app/translations/messages.pot .
pybabel update -i app/translations/messages.pot -d app/translations
# fill in any new/blank msgstr entries in the .po files, then:
pybabel compile -d app/translations
```

## License

TBD.
