from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = 'MoTA AI-GIS PoC Upgraded'
    app_host: str = '0.0.0.0'
    app_port: int = 8080
    database_url: str = 'postgresql+psycopg://poc:pocpass@127.0.0.1:5432/mota_poc'
    session_secret: str = 'change-this-session-secret'

    model_config = SettingsConfigDict(env_file='.env', extra='ignore')


settings = Settings()
