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

Authenticated API requests use `Authorization: Token <token>`.
