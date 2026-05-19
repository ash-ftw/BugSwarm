from fastapi import APIRouter

from app.core.config import settings
from app.schemas.system import LLMProviderStatus, SystemConfigResponse

router = APIRouter()


@router.get("/config", response_model=SystemConfigResponse)
def get_system_config() -> SystemConfigResponse:
    providers = [
        LLMProviderStatus(
            provider_key="groq",
            model=settings.groq_model,
            configured=bool(settings.groq_api_key),
            enabled=bool(settings.groq_api_key),
            free_mode=settings.ai_free_mode,
        ),
        LLMProviderStatus(
            provider_key="openrouter",
            model=settings.openrouter_model,
            base_url=settings.openrouter_base_url,
            configured=bool(settings.openrouter_api_key),
            enabled=bool(settings.openrouter_api_key),
            free_mode=settings.ai_free_mode,
        ),
        LLMProviderStatus(
            provider_key="gptoss",
            model=settings.gptoss_model,
            base_url=settings.gptoss_base_url,
            configured=bool(settings.gptoss_base_url),
            enabled=bool(settings.gptoss_base_url),
            free_mode=True,
        ),
        LLMProviderStatus(
            provider_key="gemini",
            model=settings.gemini_model,
            configured=bool(settings.gemini_api_key),
            enabled=bool(settings.gemini_api_key),
            free_mode=settings.ai_free_mode,
        ),
    ]
    return SystemConfigResponse(
        environment=settings.app_env,
        ai_free_mode=settings.ai_free_mode,
        providers=providers,
        default_agent_count=settings.default_agent_count,
        default_max_depth=settings.default_max_depth,
    )
