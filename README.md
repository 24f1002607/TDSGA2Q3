# 12-Factor Config Precedence — FastAPI service

## Files
- `main.py` — the service
- `config.development.yaml` — YAML layer
- `.env` — .env layer (includes the `NUM_WORKERS` alias)
- `requirements.txt` — dependencies

## Run locally
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```
Then open: http://localhost:8000/effective-config?set=port=9000&set=debug=true

## Deploy (free) on Render
1. Push these files to a GitHub repo.
2. Render.com -> New -> Web Service -> pick the repo.
3. Build command:  `pip install -r requirements.txt`
4. Start command:  `uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add Environment Variables (this is the "OS env" layer):
   - `APP_DEBUG` = `false`
   - `APP_LOG_LEVEL` = `info`
   - `APP_API_KEY` = `key-pgvcszwdms`
6. Deploy. Your endpoint is:
   `https://<your-app>.onrender.com/effective-config`

NOTE: `$PORT` is the port the host makes your app *listen* on. It is
separate from the `port` config *value* (8000/8422) that you report in JSON.
