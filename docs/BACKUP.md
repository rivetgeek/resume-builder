# Backing up the submissions database

The SQLite file used for generation history lives in the Docker volume mounted at `/app/db` inside the `api` container (see `RESUME_BUILDER_DB_PATH` in `.env`).

## Recommended approach

Run a cron job on the Synology host that copies the database safely while the container is running:

```bash
sqlite3 /var/lib/docker/volumes/<project>_db/_data/submissions.db ".backup /volume1/backups/resume-submissions-$(date +%F).db"
```

Adjust the source path to match `docker volume inspect` for the `db` volume on your system.

## Restore

Stop the stack, replace the SQLite file in the volume with your backup file (keeping permissions), then `docker compose up -d`.

## Outputs folder

Generated PDFs/HTML under `outputs/` are reproducible from YAML + templates and are **not** required for disaster recovery unless you want to keep exact historical bytes. The submissions table stores metadata and (when available) a SHA-256 of PDF output for integrity checks.
