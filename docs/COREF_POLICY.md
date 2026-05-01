# Coreference Backend Policy

**Last updated:** 2026-05-01
**Decision status:** Final — spacy-experimental-coref is the canonical backend.

---

## Decision Summary

textgraphx uses **spacy-experimental-coref** as its coreference resolution backend.
The maverick-coref service was evaluated as a potential alternative and was **rejected** due to prohibitive CPU cost in a production pipeline context.

---

## Evaluated Alternatives

| Backend | Status | Reason |
|---------|--------|--------|
| spacy-experimental-coref | **ACTIVE** | Integrated into the spaCy pipeline; no additional service required; reasonable recall. |
| maverick-coref | **DEPRECATED** | CPU-intensive inference; unacceptable p90 latency on the MEANTIME evaluation corpus. |

---

## Implementation Details

### spacy-experimental-coref

- Invoked automatically as part of the spaCy pipeline when the model includes
  the coreference component (e.g., a fine-tuned `en_coreference_web_trf` model).
- Coref clusters are read from `doc._.coref_clusters` or the equivalent
  spacy-experimental API.
- Every `REFERS_TO` edge written from coref must carry:
  - `source = 'spacy-experimental-coref'`
  - `cluster_id` — deterministic per-document integer (hash of sorted mention spans).

### maverick-coref (deprecated)

- The REST adapter (`adapters/rest_caller.py`) does **not** include a maverick
  client.
- The env-vars `MAVERICK_COREF_URL` and `TEXTGRAPHX_MAVERICK_COREF_URL` trigger
  a `DeprecationWarning` at config load time; they are otherwise ignored.
- No new code paths should reference maverick-coref.

---

## Re-evaluation Criteria

maverick-coref (or any heavier coref model) may be reconsidered if **all** of
the following conditions are met:

1. The upstream library ships a batched inference API (reducing per-sentence
   overhead to < 50 ms at p90 on the MEANTIME 120-document corpus).
2. The model is licensed permissively (MIT / Apache 2.0).
3. spacy-experimental-coref recall on MEANTIME drops below **B³ F1 = 0.70** on
   a held-out 20-document evaluation set.
4. The performance improvement justifies the operational complexity (separate
   service management, resource allocation).

Any proposal to switch coref backend must:
- Document the above metrics in a dedicated evaluation report.
- Include updated `docs/COREF_POLICY.md`, `docs/schema.md` (`REFERS_TO.source`
  values), and `CHANGELOG.md`.
- Pass a full A/B evaluation showing MEANTIME M8 scores with and without the
  new backend.

---

## Configuration

Coreference is configured entirely via spaCy; no separate service URL is
required for the canonical backend.

```toml
[services]
# coref_url is reserved for external REST-based coref services.
# Leave empty to use the spaCy pipeline coref component (canonical).
coref_url = ""
```

To completely disable coreference (e.g., for ablation experiments), remove the
coreference component from the spaCy pipeline or set an env-var guard in the
coref processor.

---

## Related Files

- `src/textgraphx/text_processing_components/CoreferenceResolver.py` — writes `REFERS_TO` edges.
- `src/textgraphx/infrastructure/config.py` — maverick deprecation warning.
- `docs/schema.md` — `REFERS_TO` edge specification.
- `DEPRECATION.md` — deprecation schedule.
