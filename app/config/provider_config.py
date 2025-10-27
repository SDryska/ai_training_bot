from dataclasses import dataclass
from typing import Dict, List, Optional

from app.providers.base import ProviderType


@dataclass(frozen=True)
class ProviderSettings:
    """Конфигурация одного вызова провайдера."""

    provider: ProviderType
    model: str


@dataclass(frozen=True)
class ProviderConfig:
    """Конфигурация провайдера с поддержкой фоллбэка."""

    primary: ProviderSettings
    fallback: Optional[ProviderSettings] = None

    def chain(self) -> List[ProviderSettings]:
        """Возвращает последовательность попыток вызова провайдеров."""
        attempts: List[ProviderSettings] = [self.primary]
        if self.fallback:
            attempts.append(self.fallback)
        return attempts


@dataclass(frozen=True)
class CaseProviderConfig:
    """Конфигурация провайдеров для кейса."""

    dialogue: ProviderConfig
    reviewer: ProviderConfig


_CASE_PROVIDER_CONFIG: Dict[str, CaseProviderConfig] = {
    "career_dialog": CaseProviderConfig(
        dialogue=ProviderConfig(
            primary=ProviderSettings(provider=ProviderType.OPENAI, model="gpt-5-mini"),
        ),
        reviewer=ProviderConfig(
            primary=ProviderSettings(provider=ProviderType.GEMINI, model="gemini-2.5-flash"),
            fallback=ProviderSettings(provider=ProviderType.OPENAI, model="gpt-5"),
        ),
    ),
    "fb_employee": CaseProviderConfig(
         dialogue=ProviderConfig(
            primary=ProviderSettings(provider=ProviderType.OPENAI, model="gpt-5-mini"),
        ),
        reviewer=ProviderConfig(
            primary=ProviderSettings(provider=ProviderType.GEMINI, model="gemini-2.5-flash"),
            fallback=ProviderSettings(provider=ProviderType.OPENAI, model="gpt-5"),
        ),
    ),
    "fb_peer": CaseProviderConfig(
         dialogue=ProviderConfig(
            primary=ProviderSettings(provider=ProviderType.OPENAI, model="gpt-5-mini"),
        ),
        reviewer=ProviderConfig(
            primary=ProviderSettings(provider=ProviderType.GEMINI, model="gemini-2.5-flash"),
            fallback=ProviderSettings(provider=ProviderType.OPENAI, model="gpt-5"),
        ),
    ),
}


def get_case_provider_config(case_id: str) -> CaseProviderConfig:
    """Возвращает конфигурацию провайдеров для кейса."""
    try:
        return _CASE_PROVIDER_CONFIG[case_id]
    except KeyError as exc:
        raise ValueError(f"Провайдеры не сконфигурированы для кейса '{case_id}'") from exc


def get_provider_chain(case_id: str, channel: str) -> List[ProviderSettings]:
    """Возвращает цепочку из primary и fallback провайдеров для канала."""
    config = get_case_provider_config(case_id)
    try:
        provider_config: ProviderConfig = getattr(config, channel)
    except AttributeError as exc:
        raise ValueError(f"Неизвестный канал провайдера '{channel}' для кейса '{case_id}'") from exc
    return provider_config.chain()
