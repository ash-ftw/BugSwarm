from __future__ import annotations

import json

from bugswarm_worker.config import settings


def main() -> None:
    startup_state = {
        "service": "bugswarm-worker",
        "status": "ready",
        "redis_url": settings.redis_url,
        "artifact_storage_root": settings.artifact_storage_root,
        "providers": {
            "groq": bool(settings.groq_api_key),
            "gptoss": bool(settings.gptoss_base_url),
            "gemini": bool(settings.gemini_api_key),
        },
    }
    print(json.dumps(startup_state, sort_keys=True))


if __name__ == "__main__":
    main()
