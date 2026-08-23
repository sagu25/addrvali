"""Minimal fakes for the AzureOpenAI client shape, so tests can exercise
the real Azure code paths (success and failure) without network access or
real credentials."""

import types


class FakeMessage:
    def __init__(self, content=None, tool_calls=None):
        self.content = content
        self.tool_calls = tool_calls


class FakeToolCall:
    def __init__(self, call_id, name, arguments):
        self.id = call_id
        self.function = types.SimpleNamespace(name=name, arguments=arguments)

    def model_dump(self):
        return {
            "id": self.id,
            "type": "function",
            "function": {"name": self.function.name, "arguments": self.function.arguments},
        }


class FakeResponse:
    def __init__(self, message: FakeMessage):
        self.choices = [types.SimpleNamespace(message=message)]


class FakeAzureClient:
    """Returns each response in `responses` in order on successive calls,
    or raises `raises` on the first call if given."""

    def __init__(self, responses=None, raises: Exception | None = None):
        self._responses = list(responses or [])
        self._raises = raises
        self.chat = types.SimpleNamespace(completions=types.SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        if self._raises is not None:
            raise self._raises
        return self._responses.pop(0)


def configure_fake_azure(monkeypatch, settings):
    """Point Settings at fake-but-well-formed Azure config so
    azure_openai_configured is True."""
    monkeypatch.setattr(settings, "azure_openai_endpoint", "https://fake.openai.azure.com/")
    monkeypatch.setattr(settings, "azure_openai_api_key", "fake-key-not-a-placeholder")
    monkeypatch.setattr(settings, "azure_openai_deployment", "fake-deployment")
