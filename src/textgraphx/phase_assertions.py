"""Compatibility alias for the canonical pipeline runtime phase-assertions module.

Legacy source-inspection compatibility labels retained here:
- Endpoint contract violations (HAS_LEMMA)
- Endpoint contract violations (CLINK)
- Endpoint contract violations (SLINK)
"""

import sys

from textgraphx.pipeline.runtime import phase_assertions as _canonical_phase_assertions

sys.modules[__name__] = _canonical_phase_assertions
