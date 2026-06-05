"""Optional LLM narration backend for DemoCreate.

The deterministic template generator (see :mod:`democreate.narration.script`)
remains the default and is never changed by this module. This adds an *optional*
upgrade: when an OpenAI-compatible API is configured via environment variables,
:class:`LLMNarrator` can generate richer narration or polish the template's
output through a chat-completions endpoint.

The module is import-safe and dependency-free. It uses only the standard library
:mod:`urllib`, and the network-touching methods are guarded — they raise
:class:`~democreate.errors.BackendUnavailableError` when no API key is configured.
The pure :func:`build_chat_payload` helper builds the request body and is fully
testable without any network access.

Example
-------
>>> payload = build_chat_payload(
...     [{"role": "user", "content": "hi"}], model="gpt-4o-mini"
... )
>>> payload["model"]
'gpt-4o-mini'
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

from .._logging import get_logger
from ..errors import BackendUnavailableError, RenderError

__all__ = [
    "llm_available",
    "build_chat_payload",
    "LLMNarrator",
    "get_narrator",
]

logger = get_logger(__name__)

# Environment variables consulted for credentials and endpoint configuration.
_API_KEY_ENV_VARS = ("OPENAI_API_KEY", "DEMOCREATE_LLM_API_KEY")
_BASE_URL_ENV_VAR = "DEMOCREATE_LLM_BASE_URL"
_DEFAULT_BASE_URL = "https://api.openai.com/v1"
_DEFAULT_MODEL = "gpt-4o-mini"
_DEFAULT_TEMPERATURE = 0.7
_REQUEST_TIMEOUT_S = 60


def _resolve_api_key() -> str | None:
    """Return the first configured API key from the environment, or ``None``.

    Returns:
        The value of ``OPENAI_API_KEY`` or ``DEMOCREATE_LLM_API_KEY`` if either is
        set to a non-empty string, otherwise ``None``.
    """
    for var in _API_KEY_ENV_VARS:
        value = os.environ.get(var)
        if value:
            return value
    return None


def llm_available() -> bool:
    """Return whether an LLM API key is configured in the environment.

    Returns:
        ``True`` if ``OPENAI_API_KEY`` or ``DEMOCREATE_LLM_API_KEY`` is set to a
        non-empty value.
    """
    return _resolve_api_key() is not None


def build_chat_payload(
    messages: list[dict],
    *,
    model: str,
    temperature: float = _DEFAULT_TEMPERATURE,
) -> dict:
    """Build the JSON body for an OpenAI-compatible ``/chat/completions`` request.

    This function is pure — it performs no I/O and makes no network call — so the
    request shape can be unit-tested directly.

    Args:
        messages: Chat messages in OpenAI format, each a mapping with ``role`` and
            ``content`` keys.
        model: Model identifier to request (e.g. ``"gpt-4o-mini"``).
        temperature: Sampling temperature for the completion.

    Returns:
        A dict ready to be JSON-encoded as the POST body, with ``model``,
        ``messages``, and ``temperature`` keys.
    """
    return {
        "model": model,
        "messages": [dict(message) for message in messages],
        "temperature": temperature,
    }


class LLMNarrator:
    """OpenAI-compatible chat client for generating or polishing narration.

    The constructor never raises on a missing key so the object can always be
    built (e.g. to inspect configuration). The network-touching methods —
    :meth:`narrate` and :meth:`rewrite_chunks` — raise
    :class:`~democreate.errors.BackendUnavailableError` when no key is configured.

    Args:
        model: Model identifier to request.
        base_url: API base URL. Falls back to ``DEMOCREATE_LLM_BASE_URL`` and then
            to ``https://api.openai.com/v1``.
        api_key: Bearer key. Falls back to ``OPENAI_API_KEY`` /
            ``DEMOCREATE_LLM_API_KEY`` from the environment.
        temperature: Default sampling temperature for requests.
    """

    name = "llm"

    def __init__(
        self,
        *,
        model: str = _DEFAULT_MODEL,
        base_url: str | None = None,
        api_key: str | None = None,
        temperature: float = _DEFAULT_TEMPERATURE,
    ) -> None:
        self.model = model
        self.temperature = temperature
        self.api_key = api_key or _resolve_api_key()
        resolved_base = base_url or os.environ.get(_BASE_URL_ENV_VAR) or _DEFAULT_BASE_URL
        self.base_url = resolved_base.rstrip("/")

    def is_available(self) -> bool:
        """Return whether this narrator has an API key to authenticate with.

        Returns:
            ``True`` if an API key was supplied or found in the environment.
        """
        return self.api_key is not None

    @property
    def endpoint(self) -> str:
        """Return the full chat-completions endpoint URL."""
        return f"{self.base_url}/chat/completions"

    def _require_key(self) -> str:
        """Return the API key or raise if none is configured.

        Returns:
            The resolved API key.

        Raises:
            BackendUnavailableError: If no API key is configured.
        """
        if not self.api_key:
            raise BackendUnavailableError("llm", extra="llm")
        return self.api_key

    def narrate(
        self, prompt: str, *, system: str | None = None, max_tokens: int = 400
    ) -> str:  # pragma: no cover - network
        """Generate narration text for ``prompt`` via the chat endpoint.

        Args:
            prompt: The user prompt describing what to narrate.
            system: Optional system instruction prepended as a system message.
            max_tokens: Upper bound on completion length.

        Returns:
            The assistant message text from the model's first choice.

        Raises:
            BackendUnavailableError: If no API key is configured.
            RenderError: On HTTP failure, JSON decode failure, or unexpected
                response shape.
        """
        key = self._require_key()

        messages: list[dict] = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        payload = build_chat_payload(
            messages, model=self.model, temperature=self.temperature
        )
        payload["max_tokens"] = max_tokens

        data = self._post(payload, key)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise RenderError(
                f"unexpected LLM response shape from {self.endpoint}: {exc}"
            ) from exc
        return str(content).strip()

    def rewrite_chunks(
        self, texts: list[str], *, context: str = ""
    ) -> list[str]:  # pragma: no cover - network
        """Polish a list of narration chunks, preserving length and order.

        The model is asked to return one polished line per input chunk as a JSON
        array. If the response cannot be parsed into a same-length list, the
        original ``texts`` are returned unchanged.

        Args:
            texts: The narration chunks to polish.
            context: Optional context describing the demo, included in the prompt.

        Returns:
            A list of polished chunks the same length as ``texts``; the input on
            any parse failure.

        Raises:
            BackendUnavailableError: If no API key is configured.
            RenderError: On HTTP failure or JSON decode failure of the transport.
        """
        self._require_key()
        if not texts:
            return []

        numbered = "\n".join(f"{i}. {text}" for i, text in enumerate(texts))
        context_line = f"Context: {context}\n\n" if context else ""
        system = (
            "You are a narration editor. Polish each numbered narration line for "
            "clarity and flow without changing its meaning. Return ONLY a JSON "
            "array of strings, one polished line per input line, in order."
        )
        prompt = (
            f"{context_line}Polish these {len(texts)} narration lines and return a "
            f"JSON array of exactly {len(texts)} strings:\n\n{numbered}"
        )
        raw = self.narrate(prompt, system=system, max_tokens=400 + 40 * len(texts))

        try:
            parsed = json.loads(raw)
        except (json.JSONDecodeError, ValueError):
            logger.warning("LLM rewrite_chunks: response was not JSON; using input")
            return list(texts)
        if not isinstance(parsed, list) or len(parsed) != len(texts):
            logger.warning(
                "LLM rewrite_chunks: parsed %s items (expected %d); using input",
                len(parsed) if isinstance(parsed, list) else "non-list",
                len(texts),
            )
            return list(texts)
        return [str(item) for item in parsed]

    def _post(self, payload: dict, key: str) -> dict:  # pragma: no cover - network
        """POST ``payload`` to the chat endpoint and return the decoded JSON.

        Args:
            payload: The request body to JSON-encode.
            key: Bearer API key.

        Returns:
            The decoded JSON response body.

        Raises:
            RenderError: On HTTP error or a non-JSON response body.
        """
        body = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(
            self.endpoint,
            data=body,
            method="POST",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {key}",
            },
        )
        try:
            with urllib.request.urlopen(
                request, timeout=_REQUEST_TIMEOUT_S
            ) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                text = response.read().decode(charset)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace") if exc.fp else ""
            raise RenderError(
                f"LLM HTTP {exc.code} from {self.endpoint}: {detail}".rstrip()
            ) from exc
        except urllib.error.URLError as exc:
            raise RenderError(f"LLM request to {self.endpoint} failed: {exc}") from exc

        try:
            return json.loads(text)
        except json.JSONDecodeError as exc:
            raise RenderError(
                f"LLM returned non-JSON from {self.endpoint}: {exc}"
            ) from exc


def get_narrator(**kwargs) -> LLMNarrator:
    """Construct an :class:`LLMNarrator`, resolving config from the environment.

    Args:
        **kwargs: Forwarded to :class:`LLMNarrator` (``model``, ``base_url``,
            ``api_key``, ``temperature``).

    Returns:
        A configured :class:`LLMNarrator` instance.
    """
    return LLMNarrator(**kwargs)
