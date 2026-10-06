from src.api.services.service_config import env_flag


def stateful_core_sourcing_enabled() -> bool:
    return env_flag("DPM_STATEFUL_CORE_SOURCING_ENABLED", False)
