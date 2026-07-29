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

## Render deployment

Use `./build.sh` as the Render build command and:

```text
python -m gunicorn Wellness_Oasis_Clinic.wsgi:application
```

as the start command. Configure `DATABASE_URL` with Render Postgres; SQLite and
uploaded media are intentionally excluded from Git. Patient uploads should use
private managed object storage before the app handles real patient information.

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
