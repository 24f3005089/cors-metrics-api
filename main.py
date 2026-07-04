from fastapi import FastAPI, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

import uuid
import time
import jwt

# ==========================
# Configuration
# ==========================

EMAIL = "YOUR_REGISTERED_EMAIL"   # Replace with your exact logged-in email

ALLOWED_ORIGIN = "https://dash-52xy3r.example.com"

ISSUER = "https://idp.exam.local"
AUDIENCE = "tds-rbhx22z6.apps.exam.local"

PUBLIC_KEY = """-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA2okOHspNjgA+2rTLbeuY
cxiP/hG8C6Sb9iwg3yiLAA4HCnpITcbWCSelbvbYGuc3EbNy4xFyf5Cbj5DHJMID
EkryOgyd2giIIIBOUBj8S63uGcnRpOBh9NFatfNwheKuzsPuVNldu6A9cNteNpXc
WyJjG2axVfmq7i6SuKr1JoWYG7xTTAvKPujSl4OtsQfO3h5NepzdfXpr28oNnzfW
ed+zclR6BcmNNo/WVfJ4xyCLSf0BCOgdTgW6PdaChd1l9VDetJZVEgC5tkyvXsfI
SI6iyrYbKR0NEBSqq4XkadEjsCs4F1RncsS4LlgniT7GlkL9Mce3b0wGLs9/7ZIX
dQIDAQAB
-----END PUBLIC KEY-----""".strip()

# ==========================
# FastAPI App
# ==========================

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[ALLOWED_ORIGIN],
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# ==========================
# Middleware
# ==========================

@app.middleware("http")
async def add_headers(request: Request, call_next):
    start = time.perf_counter()

    response = await call_next(request)

    response.headers["X-Request-ID"] = str(uuid.uuid4())
    response.headers["X-Process-Time"] = f"{time.perf_counter() - start:.6f}"

    return response

# ==========================
# Root
# ==========================

@app.get("/")
def root():
    return {"status": "running"}

# ==========================
# Question 1
# ==========================

@app.get("/stats")
def stats(values: str = Query(...)):
    nums = [int(v) for v in values.split(",")]

    total = sum(nums)

    return {
        "email": EMAIL,
        "count": len(nums),
        "sum": total,
        "min": min(nums),
        "max": max(nums),
        "mean": total / len(nums),
    }

# ==========================
# Question 2
# ==========================

class TokenRequest(BaseModel):
    token: str


@app.post("/verify")
async def verify(req: TokenRequest):
    try:
        payload = jwt.decode(
            req.token,
            PUBLIC_KEY,
            algorithms=["RS256"],
            audience=AUDIENCE,
            issuer=ISSUER,
        )

        return {
            "valid": True,
            "email": payload["email"],
            "sub": payload["sub"],
            "aud": payload["aud"],
        }

    except Exception:
        return JSONResponse(
            status_code=401,
            content={"valid": False},
        )
# ==========================
# QUESTION 3
# ==========================

import os
import yaml
from dotenv import dotenv_values
from fastapi import Query

DEFAULTS = {
    "port": 8000,
    "workers": 1,
    "debug": False,
    "log_level": "info",
    "api_key": "default-secret-000",
}

# Read .env separately so it has lower precedence than OS env
ENV_FILE = dotenv_values(".env")


def parse_bool(value):
    return str(value).strip().lower() in (
        "true",
        "1",
        "yes",
        "on",
    )


def coerce(key, value):
    if key in ("port", "workers"):
        return int(value)
    elif key == "debug":
        return parse_bool(value)
    else:
        return str(value)


@app.get("/effective-config")
async def effective_config(set: list[str] = Query(default=[])):
    config = DEFAULTS.copy()

    # Layer 2: YAML
    if os.path.exists("config.development.yaml"):
        with open("config.development.yaml", "r") as f:
            yaml_config = yaml.safe_load(f) or {}
            for k, v in yaml_config.items():
                config[k] = coerce(k, v)

    # Layer 3: .env
    env_mapping = {
        "APP_PORT": "port",
        "APP_WORKERS": "workers",
        "APP_DEBUG": "debug",
        "APP_LOG_LEVEL": "log_level",
        "APP_API_KEY": "api_key",
    }

    for env_key, cfg_key in env_mapping.items():
        if env_key in ENV_FILE:
            config[cfg_key] = coerce(cfg_key, ENV_FILE[env_key])

    # Alias: NUM_WORKERS -> workers
    if "NUM_WORKERS" in ENV_FILE:
        config["workers"] = coerce("workers", ENV_FILE["NUM_WORKERS"])

    # Layer 4: OS Environment (highest before CLI)
    for env_key, cfg_key in env_mapping.items():
        if env_key in os.environ:
            config[cfg_key] = coerce(cfg_key, os.environ[env_key])

    # Layer 5: CLI overrides
    for item in set:
        if "=" in item:
            key, value = item.split("=", 1)
            config[key] = coerce(key, value)

    # Never expose secrets
    config["api_key"] = "****"

    return config