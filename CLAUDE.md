# CLAUDE.md

Guidance for future Claude Code sessions working in this repository.

## What this is

Seam(De)Stress: a self-hosted order-management tool for a seamstress/alterations
shop. Tracks clients, per-garment alteration orders, workload planning, a service
price catalog, and invoicing. See the original build spec (provided by the user)
for full feature scope — it is not duplicated here; this file only covers
decisions and conventions.

## Architecture

- **App factory pattern**: `app/__init__.py:create_app()` builds and configures
  the Flask app. Never instantiate `Flask()` directly elsewhere.
- **Blueprints per module**, under `app/blueprints/<name>/` with `routes.py`,
  `forms.py` (WTForms), and an `__init__.py` that re-exports `bp`. Register new
  blueprints in `app/__init__.py:_register_blueprints`.
- **Models** live in `app/models/`, one file per aggregate, re-exported from
  `app/models/__init__.py` so Alembic autogenerate can see them. Shared columns
  (`created_at`/`updated_at`) come from `app/models/mixins.py:TimestampMixin`.
- **Config** is environment-driven, in `app/config.py`. Three profiles:
  `development`, `testing`, `production` (default). `get_config()` picks one
  from `FLASK_ENV`. Don't read `os.environ` outside `config.py`; add a config
  key instead.
- **Extensions** are single instances in `app/extensions.py` (db, migrate,
  login_manager, csrf, babel, limiter), initialized in `create_app`.

## Database & migrations

- SQLAlchemy 2.x via Flask-SQLAlchemy, Alembic via Flask-Migrate.
- Postgres in Docker/production; SQLite is supported for local dev only
  (`DB_DRIVER=sqlite` / `DATABASE_URL=sqlite:///...`) but is not a target for
  migrations testing — always verify migrations against Postgres before
  considering a milestone done, since column type affinity differs.
- After changing a model: `flask db migrate -m "..."` then review the
  generated migration before committing — autogenerate misses some renames
  and default-value changes.
- Migrations run automatically on container start (`scripts/entrypoint.sh`
  runs `flask db upgrade` before exec'ing gunicorn/flask). Never rely on
  manual migration steps for the Docker path.

## Auth

- Staff/admin: local username+password, Flask-Login sessions, Argon2 password
  hashing (`app/models/user.py`), CSRF via Flask-WTF, login rate-limited via
  Flask-Limiter (`LOGIN_RATE_LIMIT` config, default 10/min per IP).
- Client portal auth (tokenized per-order links, no password) is a separate
  mechanism, added in the portal milestone — do not reuse the `User` model or
  Flask-Login session for portal visitors.
- Roles: `admin`, `staff` (see `app/constants.py`). Route-level authorization
  should check `current_user.is_admin` / `current_user.is_staff_role`; there is
  no separate permissions table in v1.

## Docker / running the app

- `docker compose up -d` (using a copied `env.example` → `.env`) is the
  one-command path: builds the app image, starts Postgres, runs migrations,
  serves via gunicorn on port 5000. `GET /healthz` reports app+DB status.
- `docker compose -f docker-compose.yml -f docker-compose.dev.yml up` for live
  reload: mounts the repo into the container and runs `flask run --debug`
  instead of gunicorn.
- `flask seed` (CLI command in `app/cli.py`) creates the initial admin user
  from `ADMIN_*` env vars if one doesn't already exist, and will grow to seed
  full demo data (clients, catalog, orders) as those modules land.
- Image name: `drytrix/seamdestress`.
- **Versioned releases**: pushing a semver-shaped git tag (`v1.2.3`, matched
  by `.github/workflows/ci.yml`'s `on.push.tags` filter) runs `lint-and-test`
  as usual and then a `docker-release` job that builds and pushes
  `drytrix/seamdestress` to Docker Hub tagged with the full version,
  `major.minor`, `major`, and `latest` (via `docker/metadata-action`, with
  `flavor: latest=auto` so a pre-release tag like `v1.3.0-rc1` never
  clobbers `latest`). The existing `docker-build` job (build-only, no push,
  tagged `:ci`) still runs on ordinary branch pushes/PRs but is skipped on
  tag pushes so the image isn't built twice. Requires `DOCKERHUB_USERNAME`
  and `DOCKERHUB_TOKEN` (a Docker Hub access token, not the account
  password) as repo secrets — not something CI can self-configure. To cut a
  release: `git tag v1.2.3 && git push origin v1.2.3`.

## Frontend / look & feel

- Bootstrap 5 (not Tailwind) + a small amount of vanilla JS, HTMX where it
  helps. This is a deliberate choice matching the build spec even though the
  reference app (TimeTracker) has since migrated to Tailwind internally — only
  TimeTracker's *visual language* (colors, layout density, sidebar/topbar
  structure, card/badge conventions) is mirrored, translated into Bootstrap 5.
  Do not copy TimeTracker code.
- Base layout: `app/templates/base.html` + `app/templates/partials/`.
  Page templates extend `base.html` and fill `{% block content %}` (the
  default `{% block body %}` renders the sidebar/topbar shell around it).
  Auth and error pages override `{% block body %}` directly to skip the
  sidebar — see `app/templates/auth/login.html` for the pattern.
- Frontend assets are **vendored, not CDN-loaded** (self-hosted requirement):
  Bootstrap 5.3.8 + Bootstrap Icons 1.13.1 under `app/static/vendor/`, Inter
  (400/500/600/700, self-hosted `.woff2`) under `app/static/fonts/inter/`.
  To bump versions: `npm install bootstrap@X bootstrap-icons@Y
  @fontsource/inter@Z` in a scratch dir and copy the relevant `dist`/`files`
  output over the existing vendor files — there's no build step wired into
  this repo, the CSS/JS is used pre-compiled as-is. Theme colors/spacing are
  CSS custom-property overrides in `app/static/css/app.css` (`--bs-*` vars +
  `--sds-*` tokens), not a Sass rebuild.
- i18n: Flask-Babel, Dutch default, French/English supported. Wrap
  user-facing strings in `{{ _('...') }}` / `_('...')`. WTForms field labels
  and anything set at *import time* (not per-request) must use
  `flask_babel.lazy_gettext` (`_l`), not `gettext` — see
  `app/blueprints/auth/forms.py`. Status/type labels shown across many
  screens (`order_status_label`, `garment_type_label`, etc.) live as
  literal `_("...")` calls inside `app/__init__.py`'s context processor,
  not as dict lookups — pybabel's extractor only finds literal string
  arguments, so `_(SOME_DICT.get(code))` would silently extract nothing.
  `babel.cfg` at repo root defines extraction sources (its Jinja
  `extensions=` line was removed — `jinja2.ext.autoescape`/`with_` no
  longer exist in modern Jinja2 and crashed extraction outright; see
  Milestone 7 below). Full workflow, including the `-k lazy_gettext -k _l`
  keyword flags `pybabel extract` needs to find `_l()` calls, is in the
  README's Translations section.
- **Which locale a page renders in** depends on who it's for, not just who's
  logged in: `select_locale()` in `app/__init__.py` checks `flask.g.
  portal_locale` first (set by the portal route and by
  `orders.receipt`/`invoices.pdf` to the *client's* `preferred_language`,
  since those documents go home with the client regardless of which staff
  member generated them), then falls back to `current_user.
  preferred_language`, then `Accept-Language`. Garment tickets
  deliberately do *not* get this treatment — they stay with the garment in
  the workshop, so they render in the logged-in staff member's language.
- Flask-Babel caches the resolved locale once per request in `flask.g`.
  Changing `current_user.preferred_language` mid-request (the account
  page) needs an explicit `flask_babel.refresh()` call afterward or the
  flash message on that same request would still render in the old
  language — see `app/blueprints/auth/routes.py:account()`. Tests that
  change locale-affecting state and then expect a *second* request within
  the same test function to reflect it need the same `refresh()` call,
  because `tests/conftest.py`'s `app` fixture holds one shared app context
  open for the whole test (Flask reuses an already-active app context
  for nested test-client requests instead of pushing a fresh one, so `g`
  — and the cached locale — persists across those calls in a way it never
  would across two real, separate HTTP requests). See `tests/test_i18n.py`.

## Testing

- Pytest, fixtures in `tests/conftest.py`. `app` fixture uses the `testing`
  config profile (in-memory SQLite via `StaticPool`, CSRF disabled, rate
  limiting disabled) — fast, no Docker required for unit/route tests.
- Run locally: `pip install -r requirements-dev.txt && pytest -q`.
- Lint: `ruff check .` (config in `pyproject.toml`).

## Conventions

- No comments explaining *what* code does; only non-obvious *why*.
- Don't add abstractions, config flags, or error handling for cases that can't
  occur yet — this is a young codebase, keep it concrete until a second real
  use case justifies generalizing.
- Ask before adding scope beyond the original build spec.

## Milestone status

1. ✅ Scaffold: app factory, Docker (prod + dev compose), Postgres, Alembic,
   auth (login/logout, Argon2, CSRF, rate limiting), health check, CI
   (lint+test+docker build), styled base layout (sidebar/topbar, Bootstrap 5 +
   Bootstrap Icons + self-hosted Inter, vendored under `app/static/vendor/` —
   no CDN dependency at runtime) mirroring TimeTracker's visual language
   (indigo/teal palette, card/badge/table conventions) via a design brief,
   translated from TimeTracker's actual Tailwind implementation into Bootstrap
   5. Sidebar nav lists future sections (Clients/Orders/Planning/Catalog/
   Invoices/Settings) as disabled "Soon" placeholders — wire them up as each
   module lands.
2. ✅ Clients (`app/blueprints/clients/`: list/search, create, view, edit —
   any logged-in staff/admin) + service catalog (`app/blueprints/catalog/`:
   list/filter-by-category open to staff, create/edit/toggle-active
   admin-only via `roles_required`, see `app/utils/decorators.py`). Category
   is a plain indexed string column (`app/constants.CATALOG_CATEGORIES`), not
   a separate table — revisit only if categories need their own CRUD/ordering
   later. `flask seed` now loads 8 demo clients and 31 realistic Belgian
   alteration catalog items (repairs/zippers at 6% reduced VAT, everything
   else at 21%) from `app/seed_data.py`. Sidebar Clients/Catalog links are
   now live; Orders/Planning/Invoices/Settings stay "Soon".
3. ✅ Orders + garments + intake flow + photos + tickets
   (`app/blueprints/orders/`, models in `app/models/order.py`: `Order`,
   `Garment`, `OrderLine`, `GarmentPhoto`, `OrderStatusLog`). Notable
   decisions:
   - `Order.code` (e.g. `SDS-00007`) is a derived property from the primary
     key, not a stored/generated column — sidesteps sequence-race conditions
     entirely. The client-portal tracking token (later milestone) will be a
     separate unguessable secret, not this human-readable code.
   - Money fields are `Numeric`, never float; `OrderLine.line_total` /
     `vat_amount` are computed properties (quantized to cents) — see
     `tests/test_order_models.py` for the VAT math coverage the spec asked
     for.
   - Status flow is linear (`ORDER_STATUS_FLOW` in `app/constants.py`):
     received → in_progress → ready → picked_up, with `cancelled` as an
     always-available side branch. Every transition writes an
     `OrderStatusLog` row (who/when) — the Milestone 4 dashboard will read
     from this rather than needing its own audit trail.
   - Intake is standard full-page-reload forms, not a single AJAX/HTMX
     screen: creating an order, then adding garments and alterations on the
     order-detail "workspace" page, is a handful of clicks/submits rather
     than one continuous live-updating page. Catalog-item selection on the
     alteration line form auto-fills description/price/VAT via plain JS
     (`app/static/js/app.js`, `data-role="catalog_select"`) and stays
     editable/overridable, and items are sorted most-used-first within each
     category (`_populate_catalog_choices` in `orders/routes.py`). A
     zero-reload live-total experience is a reasonable future HTMX polish
     pass, not done here.
   - Garment tickets (`orders/ticket.html`, `orders/tickets_a4.html`) are
     print-styled HTML with `@page` CSS (80mm label width / A4 grid), not
     WeasyPrint PDFs — avoids pulling in WeasyPrint before it's actually
     needed for invoices (Milestone 6). QR codes are generated on-demand via
     `qrcode`, embedded as inline base64 PNG data URIs, no files written to
     disk. They currently link to the staff order view; a client-portal
     link is a Milestone 5 addition once that route exists.
   - Garment photos: uploaded via `app/utils/uploads.py`
     (`save_garment_photo`) — EXIF-transposed, capped to 1600px on the long
     edge, JPEG-reencoded, plus a 400px thumbnail; served through a
     login-gated `/uploads/<path:filename>` route in `app/blueprints/main`
     (not `/static`, since `UPLOAD_FOLDER` is a separate mounted volume).
   - `flask seed` now also creates 6 demo orders spanning every status
     (including one cancelled, one overdue) from `app/seed_data.py:
     DEMO_ORDERS`.
   - Client detail page now shows real order history + lifetime spend
     (`app/templates/clients/view.html`) instead of the earlier placeholder.
4. ✅ Planning/workload calendar + dashboard. Notable decisions:
   - Introduced a minimal `Settings` singleton now (`app/models/settings.py`,
     `Settings.get_solo()` auto-creates row id=1 on first access) holding
     only `daily_capacity_minutes` — planning cannot function without a
     configurable capacity, so that one field came forward from the full
     Settings milestone (branding/VAT/invoice numbering/opening hours/
     notification templates still land in Milestone 6, additively). Admin-
     only page at `/settings/`.
   - Workload math lives in `app/services/planning.py`
     (`get_daily_loads(start_date, num_days, capacity_minutes)`), shared by
     the planning week view, the dashboard, and the new-order form's
     "upcoming workload" reference panel — one place computing "minutes
     charged per day," not three. It's plain Python summing
     `Order.total_estimated_minutes` per day rather than a SQL aggregate,
     since estimated minutes is a computed property (sum of catalog
     `estimated_minutes` across garments/lines) with no DB column to
     `SUM()` — fine at this shop's scale, worth revisiting only if the order
     volume ever makes per-request full-table scans a real cost.
   - Load level thresholds (`app/services/planning.py:load_level`): green
     &lt;70% of capacity, amber 70–100%, red &gt;100% — maps directly to
     Bootstrap's `bg-success/warning/danger`, which are already retinted to
     the app palette via the `--bs-*` overrides in `app.css`, so no new CSS
     was needed for the load bars.
   - Planning week view (`/planning/?week=YYYY-MM-DD`, Monday-anchored) adds
     an always-visible Overdue panel and Express lane above the 7-day grid,
     since both matter regardless of which week is currently in view.
   - "Show which days are already full" at intake is a static 14-day
     reference list next to the new-order form (`orders/form.html`), not an
     interactive date-picker overlay — no calendar-widget JS dependency
     needed for that. Drag-and-drop rescheduling (spec called it "a plus")
     was not built.
   - Dashboard quick-actions reuse `orders.update_status` (same route the
     order-detail page uses) via a shared `main/_order_row.html` partial —
     no separate dashboard-only status-change endpoint.
   - `next_order_status()` moved from a private helper in
     `orders/routes.py` to `app/constants.py` so both the dashboard and the
     order-detail page share one definition of "what's the next status."
5. ✅ Client portal + notifications. Notable decisions:
   - `Order.portal_token` is a random `secrets.token_urlsafe(32)` string,
     distinct from `Order.code` — the code is a human-readable, guessable
     staff reference (printed on garment tickets, used for search), the
     token is the unguessable secret that grants portal access. Both can be
     public on the same document without weakening either.
   - `portal_token` is **nullable at the DB level** on purpose: rows that
     existed before this migration keep `NULL` (no auto-backfill loop in
     the migration) until someone explicitly clicks "Generate link" on that
     order; every *new* order gets one automatically via the column's
     Python-side default (`app/models/order.py:generate_portal_token`).
     Revoking sets `portal_revoked=True` without touching the token value;
     regenerating issues a fresh token and clears the revoked flag. See
     `Order.portal_active` for the combined check.
   - Migration `94e0f9b7a670` adds two NOT NULL boolean columns
     (`orders.portal_revoked`, `settings.portal_show_prices`) to already-
     populated tables — used `server_default` to backfill existing rows,
     then dropped the server default afterward so future inserts rely on
     the model's Python-side default, not DB-level drift. Verified against
     a real pre-existing (non-empty) Postgres volume, not just a fresh one.
   - Brought forward four more `Settings` fields needed for the portal to
     be meaningful (`company_name`, `company_address`, `company_phone`,
     `opening_hours`, `portal_show_prices`) — VAT defaults, invoice
     numbering, currency, and logo upload are still Milestone 6.
   - Notification templates (`app/notification_templates.py`) are plain
     Python dicts with `str.format` placeholders, deliberately **not**
     Flask-Babel `.po`/`.mo` catalogs — those are for short UI strings
     (Milestone 7's i18n pass), these are long-form email bodies per
     language (nl/fr/en) with unknown-language fallback to English.
   - Notification sending is staff-initiated ("Notify client" button on the
     order page, shown/hidden based on consent + email-on-file), not
     automatic on the ready-status transition — matches the spec's "offer
     to notify," and keeps the status-change endpoint from silently doing
     network I/O. Every attempt is logged to `NotificationLog` regardless
     of outcome (`app/services/notifications.py:notify_order_ready`); a
     missing/unreachable SMTP server logs `status="failed"` with the error
     rather than raising — the app must keep working without SMTP
     configured (`SMTP_HOST=""` is the "not configured" signal).
   - Pluggable channel registry (`app/services/notifications.py: CHANNELS`)
     — adding SMS later is a new `NotificationChannel` subclass plus one
     registry entry, not a rewrite of the calling code.
   - Garment tickets still QR-link to the staff order view (unchanged from
     Milestone 3); the new client-facing receipt
     (`GET /orders/<id>/receipt`, print-styled HTML like the tickets) QR-
     links to the portal instead — matches the spec's distinction between
     the two documents. The formal WeasyPrint quote/invoice PDF is still
     Milestone 6 scope; this receipt is a lighter HTML document that
     satisfies the portal-QR requirement now without pulling that
     dependency forward.
6. ✅ Invoices/quotes + PDFs + settings/branding
   (`app/blueprints/invoices/`, models in `app/models/invoice.py`: `Invoice`,
   `InvoiceLine`). Notable decisions:
   - **The entire `invoices` blueprint is admin-only** (`roles_required
     (ROLE_ADMIN)` on every route, including read-only list/view), unlike
     orders/clients/catalog-browsing — the spec is explicit that staff get
     "no settings/finance admin," and invoicing is squarely finance. The
     sidebar "Invoices" link is admin-gated to match; staff never see it.
   - `InvoiceLine` rows are a **snapshot copy** of the `OrderLine`s at
     invoicing time (description prefixed with the source order code for
     traceability), not a live reference — so a later edit to an order or a
     catalog price change can never retroactively alter an already-issued
     invoice. `Order.invoice_id` (nullable FK) marks an order as spoken for;
     an order can only be invoiced once (`_eligible_orders` filters on
     `invoice_id IS NULL`).
   - `Invoice.invoice_number` (e.g. `2026-0001`) is sequential **per year**
     and, unlike `Order.code`, is a real stored/unique column —
     `Invoice.generate_number(year)` queries the max existing number for
     that year prefix and increments. Single-writer assumption, documented
     in the method's docstring: fine for one shop's volume; a genuine
     concurrent create would hit the unique constraint rather than
     silently duplicate a number. "Configurable numbering format" from the
     spec was deliberately not built — the fixed `{year}-{seq:04d}` pattern
     matches the spec's own example and avoids a templating mini-language
     for a single-shop tool.
   - Invoice status is 4 explicit, manually-set values (draft/sent/paid/
     overdue) per the spec, not auto-computed from a due date — consistent
     with the rest of the app (no scheduler/cron exists anywhere here, so
     every status transition everywhere is staff-driven, not automatic).
   - Brought forward the remaining `Settings` branding fields
     (`company_vat_number`, `company_iban`, `logo_filename`) — Settings is
     now feature-complete per the original spec except notification-
     template editing (still just the hardcoded per-language templates from
     Milestone 5). Logo upload (`app/utils/uploads.py:save_logo`) keeps the
     original format (PNG stays PNG, for letterhead transparency) unlike
     garment photos, which are always re-encoded to JPEG.
   - PDF rendering (`app/services/pdf.py`) uses WeasyPrint with **inline
     base64 data URIs** for the logo (`file_data_uri`), the same pattern as
     the QR codes since Milestone 3 — no network/base_url reachability
     needed for WeasyPrint to fetch images.
   - **Dependency pin bug caught before it shipped**: `WeasyPrint==62.3`
     (a reasonable-looking pin) crashes at PDF-write time
     (`AttributeError: 'super' object has no attribute 'transform'`)
     against the pydyf version pip resolves alongside it — an
     undeclared upstream incompatibility. Caught by actually calling
     `HTML(...).write_pdf()` locally before touching Docker, not just
     `pip install`ing and assuming it worked. Pinned `WeasyPrint==69.0`
     instead, verified working both locally and inside the container.
     Runtime system libs added to the Dockerfile's `base` stage:
     `libpango-1.0-0 libpangoft2-1.0-0 libharfbuzz0b fonts-dejavu-core`
     (WeasyPrint 53+ dropped the old cairo/gdk-pixbuf PDF backend, so the
     dependency list is lighter than older WeasyPrint docs suggest).
   - Migration `e4b26f221d0b` hit a real SQLite-only bug: Alembic's
     autogenerated `batch_op.create_foreign_key(None, ...)` fails with
     `ValueError: Constraint must have a name` under SQLite's batch/table-
     recreation mode (Postgres tolerates the anonymous form fine). Fixed by
     naming the constraint explicitly (`fk_orders_invoice_id_invoices`) in
     both `upgrade()` and `downgrade()`. Worth remembering for any future
     migration that adds a FK via batch mode — always test migrations
     against SQLite too, not just Postgres, since the project supports
     both.
   - The quote/receipt PDF explicitly asked for by the spec ("simple
     receipt/quote PDF at intake") is satisfied by the existing
     `orders/receipt.html` print-styled HTML page from Milestone 5, not a
     new WeasyPrint document — it already gives the client an itemized
     estimate immediately at intake; only the formal `Invoice` needed the
     heavier WeasyPrint treatment.
   - No Peppol/e-invoicing, as the spec explicitly deferred — kept out.
7. ✅ i18n pass, tests, polish, README. Notable decisions and findings:
   - **i18n scope was deliberately bounded, not exhaustive**: fully wired
     and translated (nl + fr, English as source text) are every
     customer-facing surface — the client portal, garment tickets, the
     client receipt, and the invoice PDF — plus the staff "shell" (base
     layout, sidebar, topbar, login, dashboard, 403/404/500, and a new
     **My account** page where staff can change their own language). The
     back-office CRUD screens (clients/orders/catalog/planning/settings/
     invoices list-and-detail pages) are still English-only. This matches
     the spec's explicit emphasis on "customer-facing texts (portal,
     notifications, PDFs) translatable" being non-negotiable, while a
     full mechanical pass over every form label in ~20 more templates was
     judged lower value than the time it would cost in this pass — the
     Babel machinery, extraction workflow, and translation files are all
     in place, so extending coverage later is additive work, not a
     redesign. `app/notification_templates.py` (Milestone 5) already
     covered the "notifications" leg of that requirement separately.
   - Added `User.preferred_language` self-service via a new
     `GET/POST /auth/account` page (`app/blueprints/auth/`) — without it,
     the language infrastructure would have had no in-app way to
     exercise it beyond editing the database directly.
   - Three real, previously-undetected bugs surfaced and were fixed
     during this pass (all found by actually running the code, not by
     inspection):
     1. `babel.cfg` referenced `jinja2.ext.autoescape`/`jinja2.ext.with_`,
        both removed from modern Jinja2 — `pybabel extract` crashed
        outright on first real use. Fixed by dropping the obsolete
        `extensions=` line (autoescape is unconditional in Flask/Jinja2
        now; `with_` was inlined into core Jinja syntax long ago).
     2. HTML entities written directly inside a translatable string
        (`_('Quotes &amp; invoices')`) double-escape once Jinja's
        autoescaping runs on the *translated* output — the fix is a
        literal `&` in the msgid (`_('Quotes & invoices')`), same as any
        other template string.
     3. `orders/line_form.html` passed `data-role="description"` as a
        Python keyword argument to a WTForms field call
        (`form.description(..., data-role="...")`) — a hyphen isn't a
        valid Python identifier character, so this was a
        `TemplateSyntaxError` that crashed `GET
        /orders/<id>/garments/<id>/lines/<id>/edit` with a 500 every
        time, since Milestone 3. It went unnoticed because no test had
        ever exercised that specific GET route. Fixed with WTForms'
        underscore convention (`data_role="description"`, which the
        widget renders as `data-role="..."`). Found by writing a test for
        the edit-line page while closing a coverage gap — see below.
   - Test coverage went from 84% to 95% (`pytest --cov=app`), driven by
     `app/cli.py` (21%→96%, the `flask seed` command was essentially
     untested), `app/services/revenue.py` (18%→91%), `app/services/pdf.py`
     (58%→100%), `app/services/notifications.py` (69%→95%, added a mocked
     `smtplib.SMTP` test for the successful-send path, not just the
     unconfigured-SMTP failure path already covered), plus edit/delete
     routes for garments, photos, and order lines that had create/view
     coverage but no update/delete coverage. New i18n-specific tests
     (`tests/test_i18n.py`) lock in the locale-selection behavior
     described above. Deliberately not chasing 100% — per the spec,
     "meaningful coverage, not 100%."
   - Polish pass: a scripted sweep hit all 107 GET routes across every
     seeded record (all clients, orders, garments, lines, catalog items,
     invoices, and portal links) checking for any non-500 response —
     this is what caught bug #3 above being real and not yet fixed at
     that point, and confirmed nothing else in the app was in a similarly
     broken state.
   - README rewritten to describe the actual shipped feature set (it
     previously described the Milestone-1 aspirational plan), with a
     corrected tech-stack note (WeasyPrint is invoice-PDF-only; tickets
     and the receipt are print-styled HTML, not WeasyPrint documents) and
     a new Translations section documenting the extract/update/compile
     workflow.
   - Also closed a real spec gap noticed during this pass, not just
     scoped items: **global search** (spec section 8, "Global search
     across clients, order numbers, garment descriptions") had been left
     as a disabled topbar input with a "Coming in a later milestone"
     tooltip since Milestone 1 and never actually built in any later
     milestone. Implemented as `GET /search` in `app/blueprints/main/`
     (reuses the same order-code-parsing helper pattern as
     `orders.list_orders`) — searches clients by name/phone/email, orders
     by code or client name, and garments by description/brand/color,
     each capped at 20 results and grouped on one results page. The
     topbar input now submits there directly instead of being disabled.
8. ✅ Inventory management (`app/blueprints/inventory/`, models in
   `app/models/inventory.py`: `InventoryItem`, `StockMovement`). Added after
   the original 7-milestone spec at the user's request, so materials
   (thread, zippers, buttons, fabric, interfacing, notions) can be tracked
   and consumed on an order, then flow through to an invoice. Notable
   decisions:
   - **Inventory reaches invoices only via order lines** — `OrderLine`
     gained a second nullable FK, `inventory_item_id`, alongside the
     existing `catalog_item_id`, so a line is sourced from a service, a
     material, or neither (fully custom), enforced by a
     `validate_inventory_item_id` cross-field WTForms validator on
     `OrderLineForm` (form-level only, no DB constraint — consistent with
     not adding constraints for cases that can't occur yet). Since invoices
     are already built by copying `OrderLine`s into `InvoiceLine` snapshots
     (`invoices.create()`), this needed **zero changes to the invoices
     blueprint** — an inventory-sourced line flows onto an invoice exactly
     like a catalog-sourced one, verified end-to-end by
     `test_create_invoice_from_order_with_inventory_line_copies_snapshot`.
   - The order-line "Alteration"/"Material" selects share one `data-role`
     (`pricing_select`, renamed from `catalog_select`) so `app/static/js/
     app.js`'s existing autofill logic needed no duplication — it just also
     clears the sibling select on change, keeping the mutual-exclusivity
     rule visible client-side ahead of the server-side validator.
   - `InventoryItem.quantity_on_hand`/`low_stock_threshold` and
     `StockMovement.quantity_delta` are all `Numeric(10, 2)` (not Integer)
     so fractional stock units round-trip exactly (e.g. "used 1.5m of
     lining fabric") — deliberately a different type from
     `OrderLine.quantity` (stays `Integer`, since that counts line items,
     not stock units) and from money fields (stay `Numeric(8, 2)`, matching
     `default_price`/`unit_price` everywhere else).
   - `StockMovement` is an append-only audit log mirroring
     `OrderStatusLog` — every stock change (order-line consumption, manual
     "receive", manual "adjustment"/"waste") writes one row via
     `app/services/inventory.py:record_movement`, never mutated after
     write. `order_line_id` is nullable with `ondelete="SET NULL"` at the
     DB level (plus `passive_deletes=True` on the relationship) so deleting
     an `OrderLine` can never fail or rewrite history — only the dangling
     reference is cleared, `quantity_delta`/`reason`/`note` survive intact.
     **This exposed a real backend gap**: SQLite ignores `ON DELETE`
     actions (including `SET NULL`) unless foreign-key enforcement is
     explicitly turned on per connection, so without a fix the delete-line
     test would nul out `order_line_id` correctly on Postgres but leave it
     dangling on SQLite. Fixed by enabling `PRAGMA foreign_keys=ON` for
     every SQLite connection via an `Engine`-level `connect` event listener
     in `app/extensions.py` — this also means SQLite now enforces FKs the
     same as Postgres always has, closing a latent behavioral gap between
     the two supported backends, not just for this feature.
   - `sync_order_line_stock` (`app/services/inventory.py`) centralizes the
     reconciliation logic for all three order-line call sites (create:
     nothing → consume; edit: old quantity/item → new quantity/item; delete:
     consumed → restock) so `orders/routes.py`'s `create_line`/`edit_line`/
     `delete_line` don't duplicate the "apply delta + write audit row"
     logic three times.
   - **Negative stock is allowed**, with a flashed warning, rather than a
     hard block — a shop running out of a material mid-alteration is a
     real, legitimate situation; blocking the order line would be worse
     than a warning. No reservation/locking system, matching the existing
     single-shop, low-concurrency assumption documented on
     `Invoice.generate_number`.
   - Permissions mirror the service catalog exactly: any logged-in staff
     can browse inventory (`GET /inventory/`) and select a material on an
     order line; only admins (`roles_required(ROLE_ADMIN)`) can create/
     edit/deactivate materials or record stock receipts/adjustments. The
     sidebar "Inventory" link sits in the staff-visible "Workshop" section,
     next to Catalog.
   - `low_stock_threshold` is nullable per item, falling back to a new
     `Settings.default_low_stock_threshold` field
     (`InventoryItem.effective_low_stock_threshold`) — same additive-field,
     app-configured-not-env-configured pattern as every other `Settings`
     column, now also editable from the Settings page.
   - Migration `648c6b9841b9` adds two new tables plus a nullable FK column
     on the already-populated `order_lines` table — every new FK constraint
     is explicitly named (`fk_order_lines_inventory_item_id_
     inventory_items`, etc.), per the SQLite batch-mode anonymous-
     constraint bug already documented from `e4b26f221d0b`. Verified with
     an explicit `flask db upgrade`/`downgrade` dry run against a
     throwaway SQLite file (not just Postgres), and against the real,
     already-populated Postgres volume from earlier milestones.
   - `flask seed` gained `_ensure_demo_inventory()` (15 realistic Belgian
     alterations materials, `app/seed_data.py: INVENTORY_SEED`) and one
     `DEMO_ORDERS` garment line now references an inventory item by name
     via an `("inventory", name)` marker tuple, resolved the same way
     `catalog_by_name` resolves catalog items — this bootstrap path
     intentionally skips the `StockMovement`/`quantity_on_hand` side effect
     (it isn't going through `orders.create_line`).
