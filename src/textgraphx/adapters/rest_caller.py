import asyncio
import hashlib
import json
import logging
import re
import time
from collections import OrderedDict
from typing import List

import httpx
import requests

from textgraphx.infrastructure.config import get_config

logger = logging.getLogger(__name__)
logger.info("textgraphx.util.RestCaller module imported")

# ---------------------------------------------------------------------------
# Phase F: sentence-hash LRU cache
# ---------------------------------------------------------------------------
_SRL_CACHE_MAX = 5000

class _LruCache:
    """Thread-safe-ish ordered-dict LRU of fixed capacity."""

    def __init__(self, maxsize: int = _SRL_CACHE_MAX):
        self._maxsize = maxsize
        self._store: OrderedDict = OrderedDict()

    def _key(self, url: str, sentence: str) -> str:
        digest = hashlib.sha256(sentence.encode("utf-8")).hexdigest()
        return f"{url}:{digest}"

    def get(self, url: str, sentence: str):
        k = self._key(url, sentence)
        if k not in self._store:
            return None
        self._store.move_to_end(k)
        return self._store[k]

    def set(self, url: str, sentence: str, value) -> None:
        k = self._key(url, sentence)
        if k in self._store:
            self._store.move_to_end(k)
        self._store[k] = value
        if len(self._store) > self._maxsize:
            self._store.popitem(last=False)


_srl_cache = _LruCache()

# ---------------------------------------------------------------------------
# Phase F: per-service circuit breakers
# ---------------------------------------------------------------------------
_CB_FAILURE_THRESHOLD = 5
_CB_COOLDOWN_SEC = 30.0


class _CircuitBreaker:
    def __init__(self, threshold: int = _CB_FAILURE_THRESHOLD, cooldown: float = _CB_COOLDOWN_SEC):
        self._threshold = threshold
        self._cooldown = cooldown
        self._failures: dict = {}   # url -> consecutive count
        self._backoff_until: dict = {}  # url -> float timestamp

    def is_open(self, url: str) -> bool:
        until = self._backoff_until.get(url, 0.0)
        if time.monotonic() < until:
            return True
        # cooldown expired — reset failure counter so we try again
        if until > 0.0:
            self._failures[url] = 0
            self._backoff_until[url] = 0.0
        return False

    def record_success(self, url: str) -> None:
        self._failures[url] = 0
        self._backoff_until[url] = 0.0

    def record_failure(self, url: str) -> None:
        count = self._failures.get(url, 0) + 1
        self._failures[url] = count
        if count >= self._threshold:
            self._backoff_until[url] = time.monotonic() + self._cooldown
            logger.warning(
                "Circuit breaker OPEN for %s after %d consecutive failures; "
                "cooling down for %.0f s",
                url, count, self._cooldown,
            )


_circuit_breaker = _CircuitBreaker()


def _service_timeout() -> int:
    try:
        timeout = int(get_config().services.service_timeout_sec)
    except Exception:
        timeout = 20
    return max(1, timeout)

def amuse_wsd_api_call2(api_endpoint, sentence):
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }
    data = {"text": sentence, "lang": "EN"}
    data_json = "[" + ",".join([f'{{"text": "{item["text"]}", "lang": "{item["lang"]}"}}' for item in data]) + "]"

    try:
        logger.debug("POST %s (AMuSE-WSD) payload size=%d", api_endpoint, len(data_json))
        response = requests.post(api_endpoint, data=data_json, headers=headers, timeout=_service_timeout())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.exception("Error while calling AMuSE-WSD API: %s", e)
        return None
    
# this method has been implemented just for preprocessing input for AMUSE-WSD 
# it will replace the hyphens being used as infixes with underscores
# it appears that AMUSE-WSD consider underscores for multi-words expressions
        
def replace_hyphens_to_underscores(sentence):
    # Define a regular expression pattern to match hyphens used as infixes
    pattern = re.compile(r'(?<=\w)-(?=\w)')

    # Replace hyphens with underscores
    replaced_sentence = re.sub(pattern, '_', sentence)

    return replaced_sentence


def amuse_wsd_api_call(api_endpoint, sentences):
    headers = {
        "accept": "application/json",
        "Content-Type": "application/json"
    }

    # Apply replace_hyphens to each sentence in the collection
    # NOTE: its just a workaround for AMUSE-WSD as it does not consider hyphens for multiwords expressions
    updated_sentences = [replace_hyphens_to_underscores(sentence) for sentence in sentences]
    
    data = [{"text": sentence, "lang": "EN"} for sentence in updated_sentences]

    try:
        logger.debug("POST %s (AMuSE-WSD bulk) sentences=%d", api_endpoint, len(data))
        response = requests.post(api_endpoint, json=data, headers=headers, timeout=_service_timeout())
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        logger.exception("Error while calling AMuSE-WSD API: %s", e)
        return None
    
def callHeidelTimeService(parameters):
    dct = parameters.get("dct")
    text = parameters.get("text")

    data = {"input":text, "dct": dct}

    headers = {'Content-type': 'application/json', 'Accept': 'text/plain'}

    url = get_config().services.heideltime_url
    try:
        response = requests.post(url, json=data, headers=headers, timeout=_service_timeout())
        response.raise_for_status()
        logger.debug("HeidelTime POST to %s (dct=%s)", url, dct)
        return response.text
    except requests.exceptions.RequestException as e:
        logger.exception("Error while calling HeidelTime service: %s", e)
        return ""

def _detect_legacy_srl_schema(response_data: dict) -> bool:
    """Return True if the response looks like the old AllenNLP schema.

    The legacy AllenNLP SRL service returns ``{"verbs": [...]}`` where each
    verb entry has a ``"verb"`` key but no ``"frame"`` key.  transformer-srl
    2.4.6 returns ``"frame"`` and ``"frame_score"`` alongside ``"tags"``.
    """
    verbs = response_data.get("verbs")
    if not isinstance(verbs, list) or not verbs:
        return False
    first = verbs[0]
    return "verb" in first and "frame" not in first


def callAllenNlpApi(apiName, string):
    URL = get_config().services.srl_url

    # Phase F: cache check
    cached = _srl_cache.get(URL, string)
    if cached is not None:
        logger.debug("SRL cache hit for %s", URL)
        return cached

    # Phase F: circuit breaker check
    if _circuit_breaker.is_open(URL):
        logger.warning("SRL circuit breaker open for %s; skipping call", URL)
        return {}

    PARAMS = {"Content-Type": "application/json"}

    if apiName == 'semantic-role-labeling':
        payload = {"sentence": string}
    else:
        payload = {"document": string}

    try:
        r = requests.post(URL, headers=PARAMS, data=json.dumps(payload), timeout=_service_timeout())
        r.raise_for_status()
        logger.debug("SRL POST %s response: %s", URL, r.text)
        data = json.loads(r.text)
        _circuit_breaker.record_success(URL)
        _srl_cache.set(URL, string, data)
        if _detect_legacy_srl_schema(data):
            logger.warning(
                "SRL service at %s appears to return the legacy AllenNLP schema "
                "(no 'frame' field). Expected transformer-srl 2.4.6 on port 8010. "
                "PropBank sense and confidence will not be captured. "
                "Set srl_url=http://localhost:8010/predict or TEXTGRAPHX_SRL_URL.",
                URL,
            )
        return data
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        _circuit_breaker.record_failure(URL)
        logger.exception("Error while calling SRL API: %s", e)
        return {}


def callNominalSrlApi(sentence):
    """Call the optional CogComp nominal SRL service (single sentence).

    Returns a dict shaped as::

        {
            "words": [...],
            "frames": [
                {"predicate": "...", "predicate_index": int,
                 "sense": "acquisition.01", "sense_score": 0.97,
                 "tags": ["O","B-V","B-ARG1",...],
                 "description": "..."},
                ...
            ]
        }

    Returns ``{}`` if the service is not configured (``nom_srl_url`` empty)
    or if the request fails. Callers must treat nominal SRL output as
    optional / advisory.
    """
    url = getattr(get_config().services, "nom_srl_url", "") or ""
    if not url:
        return {}

    # Phase F: cache check
    cached = _srl_cache.get(url, sentence)
    if cached is not None:
        logger.debug("Nominal-SRL cache hit for %s", url)
        return cached

    # Phase F: circuit breaker check
    if _circuit_breaker.is_open(url):
        logger.warning("Nominal-SRL circuit breaker open for %s; skipping call", url)
        return {}

    headers = {"Content-Type": "application/json"}
    payload = {"sentence": sentence}
    try:
        r = requests.post(url, headers=headers, data=json.dumps(payload), timeout=_service_timeout())
        r.raise_for_status()
        logger.debug("Nominal-SRL response: %s", r.text)
        data = json.loads(r.text)
        _circuit_breaker.record_success(url)
        _srl_cache.set(url, sentence, data)
        return data
    except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
        _circuit_breaker.record_failure(url)
        logger.exception("Error while calling Nominal-SRL API: %s", e)
        return {}


# ---------------------------------------------------------------------------
# Phase F: async batch helpers using httpx.AsyncClient
# ---------------------------------------------------------------------------

async def _async_post_one(client: httpx.AsyncClient, url: str, payload: dict, timeout: float) -> dict:
    """Fire a single POST and return parsed JSON, or {} on error."""
    try:
        resp = await client.post(url, json=payload, timeout=timeout)
        resp.raise_for_status()
        return resp.json()
    except Exception as exc:
        logger.debug("Async SRL request to %s failed: %s", url, exc)
        return {}


async def _async_batch_srl(url: str, sentences: List[str], payload_key: str, timeout: float) -> List[dict]:
    """Send *sentences* concurrently to *url* using httpx.AsyncClient.

    Sentences that hit the cache are resolved without a network call.
    The circuit breaker is checked once before firing; if open, all sentences
    return ``{}``.

    Returns a list of response dicts in the same order as *sentences*.
    """
    if _circuit_breaker.is_open(url):
        logger.warning("SRL circuit breaker open for %s; returning empty batch", url)
        return [{} for _ in sentences]

    results: List[dict] = [None] * len(sentences)
    pending_indices: List[int] = []

    # Fill from cache
    for i, sent in enumerate(sentences):
        hit = _srl_cache.get(url, sent)
        if hit is not None:
            results[i] = hit
        else:
            pending_indices.append(i)

    if not pending_indices:
        return results  # type: ignore[return-value]

    async with httpx.AsyncClient() as client:
        tasks = [
            _async_post_one(client, url, {payload_key: sentences[i]}, timeout)
            for i in pending_indices
        ]
        responses = await asyncio.gather(*tasks)

    any_failure = False
    for idx, resp in zip(pending_indices, responses):
        if resp:
            _circuit_breaker.record_success(url)
            _srl_cache.set(url, sentences[idx], resp)
        else:
            any_failure = True
        results[idx] = resp if resp else {}

    if any_failure:
        _circuit_breaker.record_failure(url)

    return results  # type: ignore[return-value]


def callAllenNlpApiBatch(sentences: List[str]) -> List[dict]:
    """Batch verbal SRL — fires all sentences concurrently via httpx.

    Returns a list of SRL response dicts in the same order as *sentences*.
    Sentences already cached are resolved without a network call.
    Falls back to ``{}`` per sentence on circuit-breaker open or error.
    """
    url = get_config().services.srl_url
    timeout = float(_service_timeout())

    # Short-circuit: circuit open — no async needed
    if _circuit_breaker.is_open(url):
        logger.warning("SRL circuit breaker open for %s; returning empty batch", url)
        return [{} for _ in sentences]

    # Short-circuit: all sentences cached — no async needed
    results = [_srl_cache.get(url, s) for s in sentences]
    if all(r is not None for r in results):
        return results  # type: ignore[return-value]

    return asyncio.run(_async_batch_srl(url, sentences, "sentence", timeout))


def callNominalSrlApiBatch(sentences: List[str]) -> List[dict]:
    """Batch nominal SRL — fires all sentences concurrently via httpx.

    Returns a list of CogComp nominal-SRL response dicts in the same order as
    *sentences*.  Returns a list of empty dicts when the service is not
    configured.
    """
    url = getattr(get_config().services, "nom_srl_url", "") or ""
    if not url:
        return [{} for _ in sentences]
    timeout = float(_service_timeout())

    # Short-circuit: circuit open — no async needed
    if _circuit_breaker.is_open(url):
        logger.warning("Nominal-SRL circuit breaker open for %s; returning empty batch", url)
        return [{} for _ in sentences]

    # Short-circuit: all sentences cached — no async needed
    results = [_srl_cache.get(url, s) for s in sentences]
    if all(r is not None for r in results):
        return results  # type: ignore[return-value]

    return asyncio.run(_async_batch_srl(url, sentences, "sentence", timeout))


#ss = """LemonDuck's activities were first spotted in China in May 2019, before it began adopting COVID_19_themed lures in email attacks in 2020 and even the recently addressed ""ProxyLogon"" Exchange Server flaws to gain access to unpatched systems.""""
#ss = """Deutsche Bank of Germany lost almost $3.5 billion in share value, forcing the government to organize a bail_out."""
#ss = """The Federal Reserve met this week, but decided to maintain its target rate of 5.25%, although on Friday the federal funds rate was hovering around 6%, indicating a drop in liquidity."""
# ss= """Now, lenders are in a quagmire from millions of people who are unable to repay loans after taking adjustable rate mortgages, teaser rates, interest-only mortgages, or piggyback rates."""
# res_srl = callAllenNlpApi("semantic-role-labeling", ss)
# #res_srl = callAllenNlpApi("coreference-resolution", ss)


# print(res_srl)
