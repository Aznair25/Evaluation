import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock


@pytest.fixture
def mock_settings(monkeypatch):
    monkeypatch.setenv("DATABASE_URL", "postgresql+asyncpg://test:test@localhost:5432/test_db")
    monkeypatch.setenv("SECRET_KEY", "test-secret-key")
    monkeypatch.setenv("GOOGLE_CLIENT_ID", "test-client-id")
    monkeypatch.setenv("GOOGLE_CLIENT_SECRET", "test-client-secret")
    monkeypatch.setenv("OPENAI_API_KEY", "test-openai-key")
    monkeypatch.setenv("DEEPGRAM_API_KEY", "test-deepgram-key")
    monkeypatch.setenv("AZURE_SPEECH_KEY", "test-azure-key")
    monkeypatch.setenv("AWS_ACCESS_KEY_ID", "test-aws-key")
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "test-aws-secret")
    monkeypatch.setenv("AWS_S3_BUCKET", "test-bucket")
