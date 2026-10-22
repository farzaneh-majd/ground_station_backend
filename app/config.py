from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', extra='ignore')
    database_url: str = 'postgresql+asyncpg://gs:gs@localhost:5432/groundstation'
    influx_a_url: str = 'http://localhost:8086'
    influx_a_org: str = 'groundstation'
    influx_a_bucket: str = 'sat_a'
    influx_a_token: str = ''
    influx_b_url: str = 'http://localhost:8087'
    influx_b_org: str = 'groundstation'
    influx_b_bucket: str = 'sat_b'
    influx_b_token: str = ''
    ingest_api_key: str = ''
    command_api_key: str = ''
    gds_bridge_url: str = ''
    gds_bridge_token: str = ''
    command_simulation: bool = True
    sync_interval_seconds: int = 60
    cors_origins: str = 'http://localhost:3000'
    log_level: str = 'INFO'
settings = Settings()
