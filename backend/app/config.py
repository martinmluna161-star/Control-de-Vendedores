from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    supabase_url: str
    cors_origins: str = "*"

    # Render bloquea las conexiones salientes por SMTP (puertos 465/587) en
    # los servicios del plan free, así que el envío de mail va por la API
    # HTTP de SendGrid en vez de smtplib directo.
    sendgrid_api_key: str | None = None
    email_remitente: str | None = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def email_configurado(self) -> bool:
        return bool(self.sendgrid_api_key and self.email_remitente)


settings = Settings()
