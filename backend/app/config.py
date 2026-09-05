from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    supabase_url: str
    cors_origins: str = "*"

    smtp_host: str = "smtp.gmail.com"
    smtp_port: int = 465
    smtp_user: str | None = None
    smtp_password: str | None = None
    smtp_from: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def smtp_configurado(self) -> bool:
        return bool(self.smtp_user and self.smtp_password)

    @property
    def smtp_remitente(self) -> str:
        return self.smtp_from or self.smtp_user or ""


settings = Settings()
