"""
12-Factor Config Precedence service.

Merges four config layers (low -> high):
    1. defaults (hardcoded here)
    2. config.development.yaml
    3. .env file
    4. OS environment variables with the APP_ prefix
Then applies CLI overrides passed as ?set=key=value query params (highest).

We keep every value as a STRING while merging, so overriding is simple
(a later layer just replaces the string). We only convert to the final
types (int / bool / string) right at the end, when we build the response.
"""

import os
from typing import List

import yaml
from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# ----- CORS: let any web page (including the grader) call us directly -----
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----- Layer 1: hardcoded defaults (lowest precedence) -----
DEFAULTS = {
    "port": "8000",
    "workers": "1",
    "debug": "false",
    "log_level": "info",
    "api_key": "default-secret-000",
}


def load_yaml_layer() -> dict:
    """Layer 2: config.development.yaml."""
    try:
        with open("config.development.yaml") as f:
            data = yaml.safe_load(f) or {}
    except FileNotFoundError:
        return {}
    # Force everything to strings so it merges the same way as the other layers.
    return {str(k): str(v) for k, v in data.items()}


def load_dotenv_layer() -> dict:
    """Layer 3: the .env file.

    Rules:
      - APP_XXX  ->  key "xxx"       (strip the APP_ prefix, lowercase)
      - NUM_WORKERS -> key "workers" (special alias, this layer only)
    """
    result = {}
    try:
        with open(".env") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, _, value = line.partition("=")
                key, value = key.strip(), value.strip()
                if key.startswith("APP_"):
                    result[key[len("APP_"):].lower()] = value
                elif key == "NUM_WORKERS":          # the alias
                    result["workers"] = value
    except FileNotFoundError:
        pass
    return result


def load_os_env_layer() -> dict:
    """Layer 4: OS environment variables with the APP_ prefix."""
    result = {}
    for key, value in os.environ.items():
        if key.startswith("APP_"):
            result[key[len("APP_"):].lower()] = value
    return result


def to_bool(value) -> bool:
    return str(value).strip().lower() in ("true", "1", "yes", "on")


def coerce_types(merged: dict) -> dict:
    """Turn the merged string values into their real types for the response."""
    out = {}
    out["port"] = int(merged["port"])
    out["workers"] = int(merged["workers"])
    out["debug"] = to_bool(merged["debug"])
    out["log_level"] = str(merged["log_level"])
    out["api_key"] = "****"                 # never expose the real secret
    # Any extra keys (e.g. from an override) come back as plain strings.
    for k, v in merged.items():
        if k not in out:
            out[k] = str(v)
    return out


@app.get("/effective-config")
def effective_config(cli: List[str] = Query(default=[], alias="set")):
    # Merge layers low -> high. Each .update() lets a higher layer win.
    merged = {}
    merged.update(DEFAULTS)
    merged.update(load_yaml_layer())
    merged.update(load_dotenv_layer())
    merged.update(load_os_env_layer())

    # Layer 5: CLI overrides (?set=key=value), highest precedence of all.
    for item in cli:
        if "=" in item:
            key, _, value = item.partition("=")
            merged[key.strip()] = value.strip()

    return coerce_types(merged)


@app.get("/")
def root():
    return {"ok": True, "try": "/effective-config?set=port=9000&set=debug=true"}
