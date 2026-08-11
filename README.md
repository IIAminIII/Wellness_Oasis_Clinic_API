# Wellness Oasis Clinic API

Django REST API for patient identity, clinician discovery, appointments,
services, reviews, and care-desk requests.

## Local setup

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe manage.py migrate
.\.venv\Scripts\python.exe manage.py runserver
```

The local defaults use SQLite, console email, and
`http://127.0.0.1:5500` as the frontend origin. Set a real `SECRET_KEY`,
database, allowed hosts, mail provider, and HTTPS security values for deployment.

## Verification

```powershell
.\.venv\Scripts\python.exe manage.py check
.\.venv\Scripts\python.exe manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe manage.py test
```

## Demo catalogue

Populate non-patient demonstration services, doctors, and schedules:

```powershell
.\.venv\Scripts\python.exe manage.py seed_demo
```

The command is idempotent. It never creates patient accounts, appointments, or
clinical records.

## Slot capacity

Slots that existed before capacity was introduced hold one patient each. Raise
them in bulk, previewing first:

```powershell
.\.venv\Scripts\python.exe manage.py set_slot_capacity 4 --dry-run
.\.venv\Scripts\python.exe manage.py set_slot_capacity 4
```

`--weekday 5` limits it to one weekday, `--slot 3` to specific slots (repeatable),
and `--include-inactive` also covers slots that are switched off. Re-running is a
no-op. Lowering capacity below the number of patients already booked into a slot
is allowed; those appointments stand and the slot simply refuses new bookings
until it drains.

## Render deployment

Use `./build.sh` as the Render build command and:

```text
python -m gunicorn Wellness_Oasis_Clinic.wsgi:application
```

as the start command. SQLite and uploaded media are intentionally excluded from
Git. Patient uploads should use private managed object storage before the app
handles real patient information.

## Database

Any Postgres reachable through `DATABASE_URL` works; nothing in the code is tied
to a particular provider. Unset the variable to fall back to local SQLite.

### Supabase

Take the connection string from **Project settings → Database → Connection
string → URI**, and use a **pooler** host rather than the direct
`db.<ref>.supabase.co` one, which is IPv6-only and unreachable from most hosts:

| Port | Mode | Use it when |
| --- | --- | --- |
| 5432 | Session pooler | Default. Behaves like ordinary Postgres. |
| 6543 | Transaction pooler | Many short-lived connections. |

Set `DB_SSL_REQUIRE=True` alongside it. Port 6543 is detected automatically, and
persistent connections plus server-side cursors are switched off for it, because
a transaction pooler can serve consecutive statements from different backends.

Migrations run from `build.sh`, so a brand-new database only needs the variable
set; the first deploy creates the schema and seeds the demo catalogue.

## Important routes

- `GET /health/`
- `POST /patients/register/`
- `POST /patients/login/`
- `POST /patients/logout/`
- `GET|PATCH /patients/me/`
- `GET /doctors/list/`
- `GET /doctors/list/{id}/`
- `GET|POST /appointments/list/`
- `POST /appointments/list/{id}/cancel/`
- `POST /appointments/list/assisted/`
- `POST /appointments/list/{id}/transition/`
- `GET /operations/me/`
- `GET /operations/dashboard/`
- `GET|POST /operations/facilities/`
- `GET|POST /operations/departments/`
- `GET|POST /operations/roles/`

Authenticated API requests use `Authorization: Token <token>`.
