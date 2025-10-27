from dataclasses import dataclass
import pytest

from app.config.provider_config import (
    ProviderSettings,
    ProviderConfig,
    CaseProviderConfig,
    get_case_provider_config,
    get_provider_chain,
)
from app.providers.base import ProviderType


class TestProviderSettings:
    """Тесты для класса ProviderSettings"""

    def test_provider_settings_creation(self):
        """Тест: создание настроек провайдера"""
        settings = ProviderSettings(
            provider=ProviderType.OPENAI,
            model="gpt-3.5-turbo"
        )
        
        assert settings.provider == ProviderType.OPENAI
        assert settings.model == "gpt-3.5-turbo"

    def test_provider_settings_frozen(self):
        """Тест: настройки провайдера неизменяемы"""
        settings = ProviderSettings(
            provider=ProviderType.OPENAI,
            model="gpt-3.5-turbo"
        )
        
        with pytest.raises(Exception):  # dataclass(frozen=True) должен вызвать ошибку
            settings.model = "gpt-4"


class TestProviderConfig:
    """Тесты для класса ProviderConfig"""

    def test_provider_config_without_fallback(self):
        """Тест: конфигурация без fallback"""
        config = ProviderConfig(
            primary=ProviderSettings(provider=ProviderType.OPENAI, model="gpt-3.5-turbo")
        )
        
        assert config.primary.provider == ProviderType.OPENAI
        assert config.fallback is None

    def test_provider_config_with_fallback(self):
        """Тест: конфигурация с fallback"""
        config = ProviderConfig(
            primary=ProviderSettings(provider=ProviderType.OPENAI, model="gpt-3.5-turbo"),
            fallback=ProviderSettings(provider=ProviderType.GEMINI, model="gemini-2.0-flash")
        )
        
        assert config.primary.provider == ProviderType.OPENAI
        assert config.fallback.provider == ProviderType.GEMINI

    def test_provider_config_chain_without_fallback(self):
        """Тест: цепочка провайдеров без fallback"""
        config = ProviderConfig(
            primary=ProviderSettings(provider=ProviderType.OPENAI, model="gpt-3.5-turbo")
        )
        
        chain = config.chain()
        
        assert len(chain) == 1
        assert chain[0].provider == ProviderType.OPENAI

    def test_provider_config_chain_with_fallback(self):
        """Тест: цепочка провайдеров с fallback"""
        config = ProviderConfig(
            primary=ProviderSettings(provider=ProviderType.OPENAI, model="gpt-3.5-turbo"),
            fallback=ProviderSettings(provider=ProviderType.GEMINI, model="gemini-2.0-flash")
        )
        
        chain = config.chain()
        
        assert len(chain) == 2
        assert chain[0].provider == ProviderType.OPENAI
        assert chain[1].provider == ProviderType.GEMINI


class TestCaseProviderConfig:
    """Тесты для класса CaseProviderConfig"""

    def test_case_provider_config_creation(self):
        """Тест: создание конфигурации кейса"""
        config = CaseProviderConfig(
            dialogue=ProviderConfig(
                primary=ProviderSettings(provider=ProviderType.OPENAI, model="gpt-3.5-turbo")
            ),
            reviewer=ProviderConfig(
                primary=ProviderSettings(provider=ProviderType.GEMINI, model="gemini-2.0-flash")
            )
        )
        
        assert config.dialogue.primary.provider == ProviderType.OPENAI
        assert config.reviewer.primary.provider == ProviderType.GEMINI


class TestGetCaseProviderConfig:
    """Тесты для функции get_case_provider_config"""

    def test_get_case_provider_config_career_dialog(self):
        """Тест: получение конфигурации для career_dialog"""
        config = get_case_provider_config("career_dialog")
        
        assert isinstance(config, CaseProviderConfig)
        assert config.dialogue.primary.provider == ProviderType.OPENAI
        assert config.reviewer.primary.provider == ProviderType.GEMINI

    def test_get_case_provider_config_fb_employee(self):
        """Тест: получение конфигурации для fb_employee"""
        config = get_case_provider_config("fb_employee")
        
        assert isinstance(config, CaseProviderConfig)
        assert config.dialogue.primary.provider == ProviderType.OPENAI
        assert config.reviewer.primary.provider == ProviderType.GEMINI

    def test_get_case_provider_config_fb_peer(self):
        """Тест: получение конфигурации для fb_peer"""
        config = get_case_provider_config("fb_peer")
        
        assert isinstance(config, CaseProviderConfig)
        assert config.dialogue.primary.provider == ProviderType.OPENAI
        assert config.reviewer.primary.provider == ProviderType.GEMINI

    def test_get_case_provider_config_nonexistent(self):
        """Тест: получение конфигурации для несуществующего кейса"""
        with pytest.raises(ValueError) as exc_info:
            get_case_provider_config("nonexistent_case")
        
        assert "не сконфигурированы" in str(exc_info.value)


class TestGetProviderChain:
    """Тесты для функции get_provider_chain"""

    def test_get_provider_chain_dialogue(self):
        """Тест: получение цепочки для dialogue"""
        chain = get_provider_chain("career_dialog", "dialogue")
        
        assert len(chain) == 1
        assert chain[0].provider == ProviderType.OPENAI

    def test_get_provider_chain_reviewer(self):
        """Тест: получение цепочки для reviewer"""
        chain = get_provider_chain("career_dialog", "reviewer")
        
        assert len(chain) == 2
        assert chain[0].provider == ProviderType.GEMINI
        assert chain[1].provider == ProviderType.OPENAI

    def test_get_provider_chain_invalid_channel(self):
        """Тест: получение цепочки для несуществующего канала"""
        with pytest.raises(ValueError) as exc_info:
            get_provider_chain("career_dialog", "invalid_channel")
        
        assert "Неизвестный канал" in str(exc_info.value)

    def test_get_provider_chain_invalid_case(self):
        """Тест: получение цепочки для несуществующего кейса"""
        with pytest.raises(ValueError) as exc_info:
            get_provider_chain("nonexistent_case", "dialogue")
        
        assert "не сконфигурированы" in str(exc_info.value)


class TestProviderConfigIntegration:
    """Интеграционные тесты для конфигурации провайдеров"""

    def test_career_dialog_full_config(self):
        """Тест: полная конфигурация для career_dialog"""
        config = get_case_provider_config("career_dialog")
        
        # Проверяем dialogue
        dialogue_chain = config.dialogue.chain()
        assert len(dialogue_chain) == 1
        assert dialogue_chain[0].provider == ProviderType.OPENAI
        
        # Проверяем reviewer
        reviewer_chain = config.reviewer.chain()
        assert len(reviewer_chain) == 2
        assert reviewer_chain[0].provider == ProviderType.GEMINI
        assert reviewer_chain[1].provider == ProviderType.OPENAI

    def test_all_cases_have_config(self):
        """Тест: все кейсы имеют конфигурацию"""
        cases = ["career_dialog", "fb_employee", "fb_peer"]
        
        for case_id in cases:
            config = get_case_provider_config(case_id)
            assert isinstance(config, CaseProviderConfig)
            assert config.dialogue is not None
            assert config.reviewer is not None

    def test_provider_chain_order(self):
        """Тест: порядок провайдеров в цепочке"""
        chain = get_provider_chain("career_dialog", "reviewer")
        
        # Primary должен быть первым
        assert chain[0].provider == ProviderType.GEMINI
        # Fallback должен быть вторым
        assert chain[1].provider == ProviderType.OPENAI

