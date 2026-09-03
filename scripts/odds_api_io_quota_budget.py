import argparse
import json
import os
import pathlib
from datetime import datetime, timezone

STATUS_PATH = pathlib.Path("output/api_quota_status.json")
OUT_PATH = pathlib.Path("output/odds_api_io_quota_budget.json")

ROLE_DEFAULTS = {
    "feed": {"env": "BET365_MAX_ODDS_CALLS", "requested": 80, "reserve": 40},
    "closing": {"env": "CLOSING_MAX_ODDS_CALLS", "requested": 10, "reserve": 25},
    "settlement": {"env": "SETTLEMENT_MAX_EVENT_CALLS", "requested": 20, "reserve": 30},
}

REMAINING_HEADERS = (
    "x-requests-remaining",
    "x-ratelimit-remaining",
    "ratelimit-remaining",
)


def now_iso():
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def parse_int(value):
    try:
        return int(str(value).strip())
    except Exception:
        return None


def load_status(path=STATUS_PATH):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {}


def odds_api_io_entry(status):
    for entry in status.get("apis") or []:
        if str(entry.get("api") or "").lower() == "odds-api.io":
            return entry
    return {}


def remaining_requests(entry):
    headers = entry.get("headers") or {}
    for header in REMAINING_HEADERS:
        remaining = parse_int(headers.get(header))
        if remaining is not None:
            return remaining
    return None


def budget_for(role, requested=None, reserve=None, status=None):
    defaults = ROLE_DEFAULTS[role]
    requested = defaults["requested"] if requested is None else int(requested)
    reserve = defaults["reserve"] if reserve is None else int(reserve)
    status = load_status() if status is None else status
    entry = odds_api_io_entry(status)
    remaining = remaining_requests(entry)

    if remaining is None:
        allowed = requested
        mode = "default_cap_no_quota_header"
    else:
        allowed = min(requested, max(0, remaining - reserve))
        mode = "quota_aware"

    return {
        "generated_at": now_iso(),
        "api": "odds-api.io",
        "role": role,
        "env_var": defaults["env"],
        "requested_calls": requested,
        "reserve_calls": reserve,
        "remaining_calls": remaining,
        "allowed_calls": allowed,
        "mode": mode,
        "provider_configured": bool(entry.get("configured")),
        "provider_ok": entry.get("ok"),
    }


def write_env(path, env_var, value):
    if not path:
        return
    with open(path, "a", encoding="utf-8") as handle:
        handle.write(f"{env_var}={value}\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("role", choices=sorted(ROLE_DEFAULTS))
    parser.add_argument("--requested-calls", type=int)
    parser.add_argument("--reserve-calls", type=int)
    parser.add_argument("--env-file", default=os.getenv("GITHUB_ENV"))
    args = parser.parse_args()

    budget = budget_for(args.role, args.requested_calls, args.reserve_calls)
    OUT_PATH.parent.mkdir(exist_ok=True)
    OUT_PATH.write_text(json.dumps(budget, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_env(args.env_file, budget["env_var"], budget["allowed_calls"])
    print(json.dumps(budget, ensure_ascii=False))


if __name__ == "__main__":
    main()
