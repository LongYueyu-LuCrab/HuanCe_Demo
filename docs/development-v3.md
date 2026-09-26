# V3 development and release baseline

The V3 source, migration, frontend changes and regression tests are versioned together. See `workflow-v3-version.md` for the business version definition. The database's existing `workflow_version=2` is a compatibility identifier; do not rewrite it to `3`.

## Restore on a new computer

Clone `git@github.com:LongYueyu-LuCrab/HuanCe_Demo.git` and use branch `main`. Install Python 3.12 and Node.js 22.14 or a compatible newer release. Create a virtual environment, install `requirements.txt`, then install frontend dependencies using `frontend/pnpm-lock.yaml`:

```powershell
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt
cd frontend
corepack enable
corepack pnpm install --frozen-lockfile
corepack pnpm run build
cd ..
.venv/Scripts/python.exe manage.py migrate
.venv/Scripts/python.exe manage.py createsuperuser
.venv/Scripts/python.exe manage.py runserver 127.0.0.1:8000
```

Without PostgreSQL environment variables, local development uses SQLite. A fresh local database does not contain production accounts or orders. Never load production database credentials into development or test processes. The Vite configuration has no API development proxy; build the frontend and access it through Django for same-origin testing.

## Checks

```powershell
.venv/Scripts/python.exe manage.py check
.venv/Scripts/python.exe manage.py makemigrations --check --dry-run
.venv/Scripts/python.exe manage.py test core --noinput
node --test frontend/tests/rescheduling.test.cjs
```

Run the frontend build as well. Generated assets in `static/frontend/` are intentionally ignored and must be rebuilt after cloning. Do not run demo seed commands against production.

## Deployment and private materials

Production serves Django through Gunicorn and Nginx, with PostgreSQL and a separate media directory. The deployed app directory is not a Git checkout. A source commit alone does not deploy the server: build assets, back up the deployment/database, upload the reviewed release, migrate, collect static files, restart the app and verify the site.

Keep production environment files, SSH keys, databases, uploads and account/password reports outside Git. They are transferred separately through the private handoff. The full V3 workflow report contains live account credentials and is intentionally excluded; the upgrade report and this source baseline can be versioned.

Historical implementation/acceptance records in `deliverables/` describe their dated state. Current behavior removes sales scheduling confirmation for all orders while preserving sales report initial review, sample/device checks, pending-change guards and final report approval.
