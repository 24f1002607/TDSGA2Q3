import os
import yaml
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# CORS: let the grader's browser page call us from anywhere.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# The five keys we always report, in order.
CANONICAL_KEYS = ["port", "workers", "debug", "log_level", "api_key"]

# Map an env-var name (after stripping the APP_ prefix) to our key names.
# This is also where the NUM_WORKERS alias lives.
ENV_NAME_TO_KEY = {
    "PORT": "port",
    "WORKERS": "workers",
    "NUM_WORKERS": "workers",   # <-- the required alias
    "DEBUG": "debug",
    "LOG_LEVEL": "log_level",
    "API_KEY": "api_key",
}

# ---------- Layer 1: hardcoded defaults ----------
DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}


def coerce(key, value):
    """Turn a raw value into the correct type for that key."""
    if key in ("port", "workers"):
        return int(value)
    if key == "debug":
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in ("true", "1", "yes", "on")
    return str(value)


# ---------- Layer 2: config.<env>.yaml ----------
def load_yaml(env_name):
    path = f"config.{env_name}.yaml"
    if not os.path.exists(path):
        return {}
    with open(path) as f:
        data = yaml.safe_load(f) or {}
    return {k: v for k, v in data.items() if k in CANONICAL_KEYS}


# ---------- Layer 3: .env file ----------
def load_env_file(path=".env"):
    result = {}
    if not os.path.exists(path):
        return result
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            name, value = line.split("=", 1)
            name, value = name.strip(), value.strip()
            if name.startswith("APP_"):
                name = name[len("APP_"):]
            key = ENV_NAME_TO_KEY.get(name.upper())
            if key:
                result[key] = value
    return result


# ---------- Layer 4: OS env vars with APP_ prefix ----------
def load_os_env():
    result = {}
    for name, value in os.environ.items():
        if not name.startswith("APP_"):
            continue
        short = name[len("APP_"):]
        key = ENV_NAME_TO_KEY.get(short.upper())
        if key:
            result[key] = value
    return result


@app.get("/effective-config")
def effective_config(request: Request):
    env_name = os.environ.get("APP_ENV", "development")

    # Merge low -> high. Each .update() lets a higher layer win.
    merged = dict(DEFAULTS)              # layer 1
    merged.update(load_yaml(env_name))  # layer 2
    merged.update(load_env_file())      # layer 3
    merged.update(load_os_env())        # layer 4

    # ---------- Layer 5: CLI overrides (?set=key=value) ----------
    for raw in request.query_params.getlist("set"):
        if "=" in raw:
            k, v = raw.split("=", 1)
            k = k.strip()
            k = ENV_NAME_TO_KEY.get(k.upper(), k)  # allow alias here too
            merged[k] = v

    # Build the response with correct types, only the five keys.
    result = {key: coerce(key, merged[key]) for key in CANONICAL_KEYS}

    # Never expose the real secret.
    result["api_key"] = "****"
    return result


@app.get("/")
def root():
    return {"ok": True, "try": "/effective-config"}
