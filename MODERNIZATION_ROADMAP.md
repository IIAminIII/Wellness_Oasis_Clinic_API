# Wellness Oasis modernization roadmap

This roadmap treats Wellness Oasis as a real healthcare product, not only a
booking website. Each phase should ship as a tested, deployable increment.

## Phase 1 — trustworthy patient access (completed)

- Upgrade to supported Django and Django REST Framework releases.
- Make configuration environment-driven and safe to start locally.
- Repair registration, email/username login, token rotation, logout, and profile.
- Create patient profiles automatically and enforce record ownership.
- Protect administrative API writes and private contact requests.
- Add appointment dates, slot validation, double-booking protection, ownership,
  cancellation, status tracking, and database indexes.
- Consolidate the frontend into a responsive design system without Tailwind CDN.
- Add patient portal, doctor discovery, booking, profile editing, and care desk.
- Add backend regression tests and browser verification of the complete journey.

## Phase 2 — hospital operations and access control (in progress)

The first Phase 2 slice establishes explicit multi-role assignments, facilities,
departments, role-aware dashboards, receptionist-assisted booking, guarded
appointment transitions, and append-only audit events. Scheduling capacity,
waitlists, stronger session authentication, and the remaining workforce modules
continue as separate deployable slices.

- Replace the implicit Django user roles with explicit Patient, Doctor, Nurse,
  Receptionist, Billing, Lab Technician, Pharmacist, and Administrator roles.
- Add facilities, departments, rooms, beds, shifts, doctor leave, recurring
  schedules, slot capacity, waitlists, and receptionist-assisted bookings.
- Introduce short-lived authentication, refresh rotation, device/session
  management, password reset, optional MFA, and account recovery.
- Add audit events for viewing or changing sensitive records.
- Build role-specific dashboards and an operations-focused component library.
- Add API schema documentation, CI checks, and end-to-end role tests.

## Phase 3 — clinical records

- Patient demographics, emergency contacts, allergies, conditions, and consent.
- Encounters, triage, vitals, clinical notes, diagnoses, care plans, and follow-up.
- Prescriptions, medication reconciliation, laboratory and imaging orders/results.
- Secure document upload, access history, retention rules, and export workflows.
- Fine-grained clinical permissions and break-glass emergency access.

## Phase 4 — billing, communications, and patient engagement

- Service catalogue pricing, invoices, discounts, refunds, and payment ledger.
- Insurance policies, claims, pre-authorisation, and reconciliation workflows.
- Email/SMS/in-app reminders, notification preferences, and delivery history.
- Telehealth sessions, clinician messaging, queue status, and satisfaction surveys.
- Localisation, accessible patient content, and caregiver/dependent access.

## Phase 5 — production hardening and scale

- PostgreSQL, managed object storage, Redis, background jobs, and idempotent tasks.
- Structured logs, error tracking, metrics, traces, alerting, and audit review.
- Encrypted backups, restore drills, disaster recovery targets, and key rotation.
- Threat modelling, dependency scanning, penetration testing, and privacy review.
- Load tests, query budgets, caching, image optimisation, and uptime objectives.
- Staging/production CI/CD with reversible migrations and release runbooks.

## Definition of hospital-grade

Phase 1 is a strong booking and patient-access foundation. The product should not
store full clinical records or claim regulatory compliance until Phases 2–5 have
been implemented and reviewed against the laws, policies, and clinical workflows
of the deployment country.
