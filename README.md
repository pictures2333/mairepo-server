# mairepo

## 測試資料庫

啟動測試用 PostgreSQL：

```sh
docker compose -f docker-compose.yaml -f docker-compose.test.yaml up -d db
```

在 host 端執行測試時，將 `.env` 的資料庫連線設定為 host 可連線的位址：

```env
DATABASE_URL=postgresql+asyncpg://mairepo:change_me@127.0.0.1:5432/mairepo
```

關閉測試用 PostgreSQL：

```sh
docker compose -f docker-compose.yaml -f docker-compose.test.yaml down
```

## 資料庫 Migration

將資料庫 schema migrate 到最新版本：

```sh
uv run alembic upgrade head
```

更新 `src/database/model.py` 後，產生 migration，並檢查 `migrations/versions/` 內產生的檔案：

```sh
uv run alembic revision --autogenerate -m "describe the schema change"
uv run alembic upgrade head
```
