# mairepo

mairepo is a chart repository server.

It downloads charts from Google Drive and provides an HTTP API for clients to browse and download them.

Client: [mairepo-client](https://github.com/pictures2333/mairepo-client)

## Google Drive layout

`MAISQUARED_FOLDER_ID` must identify the root folder of the following three-level layout:

```text
<MAISQUARED_FOLDER_ID>
└── 1. Generation name
    └── Chart name
        ├── bg.jpg
        ├── maidata.txt
        ├── pv.mp4
        └── track.mp3
```

Each level has a specific purpose:

- The first level contains generation folders. Their names must match `<number>[.<number>...][letters]. <name>`, such as `1. maimai`, `2. maimai PLUS`, or `12.5A. Example`.
- The second level contains chart folders. Each folder must use the chart name, and chart names must be unique across the repository.
- The third level contains only the files that make up a chart; nested folders are not supported. A chart commonly contains `bg.jpg`, `maidata.txt`, `pv.mp4`, and `track.mp3`.

Share the root folder with the configured service account.

Use the folder ID from its Google Drive URL, not the entire URL.

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

- `GET /chart/` returns all charts, their files, and the newest `GC_KEEP` blobs for each file.
- `GET /chart/{chart_id}` returns a specific chart using the same schema.
- `GET /blob/{blob_id}` downloads a retained blob.

When `TOKEN` is configured, send it in the `MAIREPO_TOKEN` request header.

The chart index orders blobs from newest to oldest. A client should try the newest blob first and fall back to an older returned blob if the download is temporarily unavailable.

## Docker deployment

mairepo can be deployed with Docker Compose.

**Do not scale the application service or start Uvicorn with multiple workers. Synchronization, garbage collection, and integrity checking use an in-process lock and assume a single writer.**

1. Create the environment file:

   ```sh
   cp .env.example .env
   ```

2. Set `MAISQUARED_FOLDER_ID` and `TOKEN`, then customize any other values as needed in `.env`.

   `.env.example` already provides the paths and hostnames required to run inside the containers.

3. Change the default `change_me` database password in both `.env` and `docker-compose.yml`.

   The password in `DATABASE_URL` and the value in `POSTGRES_PASSWORD` must remain identical.

4. Save the service account credential as `mairepo-service-account.json` and restrict its permissions:

   ```sh
   chmod 600 mairepo-service-account.json
   ```

5. Build and start the services:

   ```sh
   docker compose -f docker-compose.yml up -d --build
   ```

   The API is available on port `8080` after the application starts.

6. Inspect logs or stop the deployment:

   ```sh
   docker compose -f docker-compose.yml logs -f mairepo
   docker compose -f docker-compose.yml down
   ```

## Development

### Install dependencies manually

```sh
uv sync --frozen
```

### Start the test database manually

Start PostgreSQL and expose it to the host:

```sh
docker compose -f docker-compose.yml -f docker-compose.test.yml up -d db
```

The default test database password is `change_me`.

For host-side development, replace the Docker-specific database hostname, storage path, and credential path in `.env`:

```env
DATABASE_URL=postgresql+asyncpg://mairepo:change_me@127.0.0.1:5432/mairepo
DIRECTORY=./example_storage
GOOGLE_SERVICE_ACCOUNT_CRED_FILE=./mairepo-service-account.json
```

Stop the test database when it is no longer needed:

```sh
docker compose -f docker-compose.yml -f docker-compose.test.yml down
```

### Manage database migrations manually

Upgrade the database to the latest revision:

```sh
uv run alembic upgrade head
```

After changing `src/database/model.py`, generate and inspect a migration, then apply it:

```sh
uv run alembic revision --autogenerate -m "describe the schema change"
uv run alembic upgrade head
```

### Run the application manually

```sh
mkdir -p example_storage
./run.sh
```
