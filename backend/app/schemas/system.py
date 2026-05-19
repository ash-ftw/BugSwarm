from pydantic import BaseModel


class LLMProviderStatus(BaseModel):
    provider_key: str
    model: str
    configured: bool
    enabled: bool
    free_mode: bool
    base_url: str | None = None


class SystemConfigResponse(BaseModel):
    environment: str
    ai_free_mode: bool
    providers: list[LLMProviderStatus]
    default_agent_count: int
    default_max_depth: int
