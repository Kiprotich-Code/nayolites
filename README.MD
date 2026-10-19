# College Management System

A Django web application for managing college accounts, students, courses,
enrollments, fees, payments, results, and course materials.

## Run locally

You need Python 3.12 or newer.

1. Create and activate a virtual environment:

   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

   On macOS/Linux, use `python3 -m venv .venv` and
   `source .venv/bin/activate`.

2. Install dependencies and create your private settings file:

   ```powershell
   python -m pip install -r requirements.txt
   Copy-Item .env.example .env
   ```

   On macOS/Linux, use `cp .env.example .env`.

   Generate a secret key:

   ```powershell
   python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
   ```

   Put the generated value after `SECRET_KEY=` in `.env`. Never commit `.env`.
   You can also change the institution details in `.env`.

3. Set up the database and start the site:

   ```powershell
   python manage.py migrate
   python manage.py create_initial_groups
   python manage.py createsuperuser
   python manage.py runserver
   ```

   Open <http://127.0.0.1:8000/>.

## Before production

- Use PostgreSQL by setting `DB_ENGINE=django.db.backends.postgresql` and
  providing `DB_NAME`, `DB_USER`, `DB_PASSWORD`, `DB_HOST`, and `DB_PORT`.
  Set `DB_SSLMODE=require` when your provider supports TLS.
- Set a unique `SECRET_KEY`, `DEBUG=False`, `ALLOWED_HOSTS` to your domain,
  and `CSRF_TRUSTED_ORIGINS` to your HTTPS origin (for example,
  `https://college.example`).
- Configure email and, if used, PayHero credentials and the public
  `PAYHERO_CALLBACK_URL`.
- With `DEBUG=False`, HTTPS redirects and secure session/CSRF cookies are on
  by default. Set `TRUST_X_FORWARDED_PROTO=True` only if your trusted hosting
  proxy overwrites `X-Forwarded-Proto`. Enable HSTS only after confirming the
  domain and all required subdomains are HTTPS.
- Set secrets in your hosting provider's environment settings; do not upload
  `.env` or commit secrets. Rotate credentials previously stored in source
  control; deleting them from current files does not remove them from Git history.
- The local SQLite database is excluded from the current repository tree.
  Purge earlier copies from Git history before making the repository public.

Run `python manage.py check --deploy` with production settings before release.
