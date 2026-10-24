# mairepo

mairepo is a single-instance chart package repository server. It synchronizes
chart files from Google Drive, keeps revision history in PostgreSQL, retains
downloadable blobs on local storage, and exposes the repository through a
FastAPI HTTP API.

## Google Drive layout

`MAISQUARED_FOLDER_ID` must identify the root folder of a fixed three-level
layout:

```text
<MAISQUARED_FOLDER_ID>
├── 1. Generation name
│   ├── Chart name A
│   │   ├── chart-file-1
│   │   └── chart-file-2
│   └── Chart name B
│       └── chart-file-1
└── 2. Another generation
    └── Chart name C
        └── chart-file-1
```

The following rules are required:

- Generation folder names must match `<number>[.<number>...][letters]. <name>`.
  Examples include `1. maimai`, `2. maimai PLUS`, and `12.5A. Example`.
- Only direct child folders of a generation folder are treated as charts.
- Only direct child files of a chart folder are synchronized. Nested folders
  inside a chart folder are ignored.
- Chart folder names must be unique across every generation folder.
- File names must be unique within each chart folder.
- Chart files must be downloadable binary Google Drive files that provide an
  MD5 checksum and a `headRevisionId`. Native Google Docs, Sheets, and Slides
  files are not supported.
- The service account configured by `GOOGLE_SERVICE_ACCOUNT_CRED_FILE` must
  have read access to the root folder and its contents. Sharing the folder
  directly with the service account is recommended.

Use the folder ID from the Google Drive URL, not the entire URL.

## Environment variables

Copy `.env.example` to `.env` and update the required values.

| Variable | Required | Default | Description |
| --- | --- | --- | --- |
| `DATABASE_URL` | Yes | None | SQLAlchemy async PostgreSQL URL. Use the `db` hostname inside Docker Compose and `127.0.0.1` when running on the host. |
| `MAISQUARED_FOLDER_ID` | Yes | None | Google Drive ID of the repository root folder described above. |
| `GOOGLE_SERVICE_ACCOUNT_CRED_FILE` | Yes | None | Path to the Google service account JSON credential file. The account only needs Drive read access. |
| `SYNC_CONCURRENCY` | No | `8` | Maximum number of concurrent Google Drive synchronization operations. |
| `RUN_SYNC_INTERVAL` | No | `3600` | Delay in seconds between synchronization runs. |
| `DIRECTORY` | Yes | None | Existing directory used to store downloaded blob files. Startup fails when it is unavailable. |
| `GC_KEEP` | No | `3` | Number of newest blobs per file exposed by the API. |
| `GC_MAX_KEEP` | No | `7` | Number of newest blobs per file retained before garbage collection. Must be greater than or equal to `GC_KEEP`. |
| `RUN_GC_INTERVAL` | No | `43200` | Delay in seconds between garbage-collection runs. |
| `RUN_CHECK_INTERVAL` | No | `86400` | Delay in seconds between storage integrity checks. |
| `TOKEN` | No | Empty | Expected value of the `MAIREPO_TOKEN` request header. An empty value disables API authentication. |
| `MAX_ATTEMPTS` | No | `3` | Maximum number of attempts for retryable Google Drive operations. |

## API

- `GET /chart/` returns all charts, their files, and the newest `GC_KEEP`
  blobs for each file.
- `GET /chart/{chart_id}` returns a specific chart using the same schema.
- `GET /blob/{blob_id}` downloads a retained blob.

When `TOKEN` is configured, send it in the `MAIREPO_TOKEN` request header.
The chart index orders blobs from newest to oldest. A client should try the
newest blob first and fall back to an older returned blob if the download is
temporarily unavailable.

## Docker deployment

The provided Dockerfile builds the Python environment into the application
image. Compose runs one mairepo application instance and one PostgreSQL
instance. Do not scale the application service or start Uvicorn with multiple
workers: synchronization, garbage collection, and integrity checking use an
in-process lock and assume a single writer.

1. Create the environment file:

   ```sh
   cp .env.example .env
   ```

2. Set `MAISQUARED_FOLDER_ID`, `TOKEN`, and any desired intervals in `.env`.
   The values in `.env.example` already use the paths and hostnames expected
   inside the containers.

3. Change the default `change_me` database password in both `.env` and
   `docker-compose.yml`. The password in `DATABASE_URL` and the value in
   `POSTGRES_PASSWORD` must remain identical.

4. Save the service account credential as `mairepo-service-account.json` and
   restrict its permissions:

   ```sh
   chmod 600 mairepo-service-account.json
   ```

   The file is ignored by Git and mounted as a Compose secret.

5. Build and start the services:

   ```sh
   docker compose -f docker-compose.yml up -d --build
   ```

   The application automatically runs `alembic upgrade head` before starting
   Uvicorn. The API is available on port `8080`.

6. Inspect logs or stop the deployment:

   ```sh
   docker compose -f docker-compose.yml logs -f mairepo
   docker compose -f docker-compose.yml down
   ```

PostgreSQL data and downloaded blobs are stored in named Docker volumes. The
Python environment is installed into the application image at build time.

## Development

Install dependencies:

```sh
uv sync --frozen
```

Start only the test PostgreSQL service and expose it to the host:

```sh
docker compose -f docker-compose.yml -f docker-compose.test.yaml up -d db
```

The default test database password is `change_me`. For host-side development,
replace the Docker-specific database hostname, storage path, and credential
path in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://mairepo:change_me@127.0.0.1:5432/mairepo
DIRECTORY=./storage
GOOGLE_SERVICE_ACCOUNT_CRED_FILE=./mairepo-service-account.json
```

Apply all database migrations:

```sh
uv run alembic upgrade head
```

After changing `src/database/model.py`, generate and inspect a migration,
then apply it:

```sh
uv run alembic revision --autogenerate -m "describe the schema change"
uv run alembic upgrade head
```

Run the API locally:

```sh
mkdir -p storage
./run.sh
```

Stop the test database:

```sh
docker compose -f docker-compose.yml -f docker-compose.test.yaml down
```
