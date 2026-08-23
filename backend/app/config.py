import os

from dotenv import load_dotenv

load_dotenv()


class Settings:
    azure_openai_endpoint: str = os.getenv("AZURE_OPENAI_ENDPOINT", "")
    azure_openai_api_key: str = os.getenv("AZURE_OPENAI_API_KEY", "")
    azure_openai_deployment: str = os.getenv("AZURE_OPENAI_DEPLOYMENT", "")
    azure_openai_api_version: str = os.getenv(
        "AZURE_OPENAI_API_VERSION", "2024-02-15-preview"
    )

    cors_origins: list[str] = os.getenv(
        "CORS_ORIGINS", "http://localhost:5173"
    ).split(",")

    @property
    def azure_openai_configured(self) -> bool:
        placeholder_markers = ("REPLACE_ME", "your-", "changeme", "")
        return (
            bool(self.azure_openai_endpoint)
            and bool(self.azure_openai_api_key)
            and bool(self.azure_openai_deployment)
            and not any(
                marker.lower() in self.azure_openai_api_key.lower()
                for marker in placeholder_markers
                if marker
            )
        )


settings = Settings()
