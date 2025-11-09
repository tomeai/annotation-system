from functools import lru_cache
from pathlib import Path
from typing import Literal, Any

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_PATH = Path(__file__).resolve().parent


class Settings(BaseSettings):
    """全局配置"""

    model_config = SettingsConfigDict(
        env_file=f'{BASE_PATH}/.env',
        env_file_encoding='utf-8',
        extra='ignore',
        case_sensitive=True,
    )

    # .env 当前环境
    ENVIRONMENT: Literal['dev', 'prod'] = 'dev'

    # FastAPI
    FASTAPI_API_V1_PATH: str = '/api/v1'
    FASTAPI_TITLE: str = 'FastAPI'
    FASTAPI_DESCRIPTION: str = 'FastAPI Best Architecture'
    FASTAPI_DOCS_URL: str = '/docs'
    FASTAPI_REDOC_URL: str = '/redoc'
    FASTAPI_OPENAPI_URL: str | None = '/openapi'
    FASTAPI_STATIC_FILES: bool = True

    @model_validator(mode='before')
    @classmethod
    def check_env(cls, values: Any) -> Any:
        """检查环境变量"""
        if values.get('ENVIRONMENT') == 'prod':
            # FastAPI
            values['FASTAPI_OPENAPI_URL'] = None
            values['FASTAPI_STATIC_FILES'] = False

            # task
            values['CELERY_BROKER'] = 'rabbitmq'

        return values


@lru_cache
def get_settings() -> Settings:
    """获取全局配置单例"""
    return Settings()


# 创建全局配置实例
settings = get_settings()
