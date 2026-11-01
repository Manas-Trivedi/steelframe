"""Providers with a free tier. Each turns (system, user) into text plus token counts."""
import os
import urllib.request
from collections import namedtuple

from .errors import AuthError, NotFree, Rejected, Unavailable
from .http import request_json

# `detail` says how the model stopped (finish reason, thinking tokens), so a bad answer can be told from a cut-off one.
Result = namedtuple("Result", "text tokens_in tokens_out provider model detail", defaults=("",))


class Provider:
    def __init__(self, name, base_url, key_env, opener=None):
        self.name, self.base_url, self.key_env = name, base_url.rstrip("/"), key_env
        self.opener = opener or urllib.request.urlopen

    def key(self):
        key = os.environ.get(self.key_env, "").strip()
        if not key:
            raise AuthError(f"{self.key_env} is not set")
        return key

    def check_free(self, model):
        """Raise NotFree if this model is known not to be free. Others are free by the key's plan."""

    def _call(self, url, headers, payload=None, timeout=60):
        return request_json(url, headers=headers, payload=payload, timeout=timeout, opener=self.opener)


class OpenAICompatible(Provider):
    """Groq and OpenRouter. Both speak the OpenAI chat format."""

    def check_free(self, model):
        if self.name == "openrouter" and not model.endswith(":free"):
            raise NotFree(f"openrouter model '{model}' does not end in ':free'")

    def complete(self, model, system, user, json_mode=True, max_tokens=4096):
        self.check_free(model)
        payload = {"model": model, "max_tokens": max_tokens,
                   "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}]}
        if json_mode:
            payload["response_format"] = {"type": "json_object"}
        reply = self._call(f"{self.base_url}/chat/completions", {"Authorization": f"Bearer {self.key()}"}, payload)
        try:
            choice = reply["choices"][0]
            text = choice["message"]["content"] or ""
        except (KeyError, IndexError, TypeError) as error:
            raise Unavailable(f"unexpected reply shape: {str(reply)[:150]}") from error
        usage = reply.get("usage") or {}
        return Result(text, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0), self.name, model,
                      f"finish_reason={choice.get('finish_reason')}")

    def list_models(self):
        reply = self._call(f"{self.base_url}/models", {"Authorization": f"Bearer {self.key()}"})
        ids = sorted(m["id"] for m in reply.get("data", []))
        return [i for i in ids if i.endswith(":free")] if self.name == "openrouter" else ids


class Gemini(Provider):
    def complete(self, model, system, user, json_mode=True, max_tokens=4096):
        payload = {
            "systemInstruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {"maxOutputTokens": max_tokens},
        }
        if json_mode:
            payload["generationConfig"]["responseMimeType"] = "application/json"
        reply = self._call(f"{self.base_url}/models/{model}:generateContent", {"x-goog-api-key": self.key()}, payload)
        candidates = reply.get("candidates") or []
        if not candidates:
            raise Rejected(f"no candidates (blocked?): {str(reply.get('promptFeedback', reply))[:150]}")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        text = "".join(p.get("text", "") for p in parts)
        if not text:
            raise Rejected(f"empty answer, finishReason={candidates[0].get('finishReason')}")
        usage = reply.get("usageMetadata") or {}
        return Result(text, usage.get("promptTokenCount", 0), usage.get("candidatesTokenCount", 0), self.name, model,
                      f"finishReason={candidates[0].get('finishReason')}, thoughtsTokens={usage.get('thoughtsTokenCount', 0)}")

    def list_models(self):
        reply = self._call(f"{self.base_url}/models?pageSize=200", {"x-goog-api-key": self.key()})
        return sorted(m["name"].split("/", 1)[-1] for m in reply.get("models", [])
                      if "generateContent" in m.get("supportedGenerationMethods", []))


KINDS = {"openai": OpenAICompatible, "gemini": Gemini}


def build_providers(config, opener=None):
    return {name: KINDS[spec["kind"]](name, spec["base_url"], spec["key_env"], opener)
            for name, spec in config["providers"].items()}
