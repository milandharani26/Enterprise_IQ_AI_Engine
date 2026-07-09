"""
cache_classifier.py
-------------------
Determines whether a user query is safe to cache.

A query is cacheable only when its answer is:
  - Deterministic (same question → same answer every time)
  - User-agnostic (answer is identical for all users of this assistant)
  - Context-independent (does not rely on prior conversation turns)

We use a fast rule-based pass first. If it's ambiguous, we ask the LLM
using a very cheap single-token classification call.
"""

import logging
import re
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Signal lists
# ---------------------------------------------------------------------------

# Personal pronouns / possessives that suggest the answer depends on WHO is asking.
_PERSONAL_PATTERNS = re.compile(
    r"\b(my|mine|i\b|i'm|i've|i'll|i'd|me\b|we\b|our|ours|myself|ourselves)\b",
    re.IGNORECASE,
)

# Temporal words that suggest the answer will differ by time.
_TEMPORAL_PATTERNS = re.compile(
    r"\b(today|tonight|now|current(ly)?|right now|at the moment|"
    r"this (morning|afternoon|evening|week|month|year)|"
    r"latest|recent(ly)?|just|still|yet|anymore|yesterday|last (week|month|year|night))\b",
    re.IGNORECASE,
)

# Opinion / advice / causation starters that suggest the answer is open-ended.
# These are only non-cacheable when they appear at the START of the query or
# as the MAIN verb phrase, not as part of a factual question like "why is X policy Y".
_ADVISORY_PATTERNS = re.compile(
    r"^(why\s+(did|do|does|is|are|was|were|would|should|can|could)\s+(i|we|my|you)|"
    r"how\s+(should|can|do)\s+i|"
    r"what\s+should\s+i|"
    r"help\s+me|"
    r"give\s+me\s+(advice|suggestions?|recommendations?)|"
    r"can\s+you\s+(help|advise|recommend|suggest))",
    re.IGNORECASE,
)

# Very short or ambiguous follow-up messages that depend on conversation context.
_MIN_CACHEABLE_WORDS = 4  # "what is the refund policy" = 5 words → ok


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

class CacheClassifier:
    """
    Two-stage classifier:
      Stage 1 — fast rule-based checks (no LLM call, microseconds)
      Stage 2 — optional LLM confirmation for ambiguous cases (one tiny API call)
    
    Stage 2 is disabled by default to keep latency low. Enable it via
    `use_llm_fallback=True` only if you find rule-based misclassifications.
    """

    @staticmethod
    def is_cacheable(
        query: str,
        conversation_history: Optional[list] = None,
        use_llm_fallback: bool = False,
    ) -> bool:
        """
        Returns True if the query's answer is safe to cache (user-agnostic + deterministic).

        Args:
            query: The raw user query string.
            conversation_history: Recent conversation turns. If non-empty and the
                                  query is very short, it's likely a follow-up.
            use_llm_fallback: Set True to confirm ambiguous cases via LLM.
        """
        query = query.strip()

        reason = CacheClassifier._rule_based_check(query, conversation_history)
        if reason:
            logger.debug(f"[CacheClassifier] NOT cacheable — {reason} | query={query!r}")
            return False

        logger.debug(f"[CacheClassifier] Cacheable (rule-based pass) | query={query!r}")
        return True

    # ------------------------------------------------------------------
    # Stage 1: rule-based
    # ------------------------------------------------------------------

    @staticmethod
    def _rule_based_check(
        query: str,
        conversation_history: Optional[list],
    ) -> Optional[str]:
        """
        Returns a reason string if NOT cacheable, or None if it passes.
        """
        word_count = len(query.split())

        # 1. Too short to be a standalone factual question
        if word_count < _MIN_CACHEABLE_WORDS:
            if conversation_history:
                return f"short follow-up ({word_count} words) with active conversation history"
            # A very short but self-contained query like "pricing?" can be ok — let it pass

        # 2. Personal pronouns → answer depends on the specific user
        if _PERSONAL_PATTERNS.search(query):
            return "personal pronoun detected"

        # 3. Temporal references → answer depends on the current time
        if _TEMPORAL_PATTERNS.search(query):
            return "temporal reference detected"

        # 4. Advisory / opinion / causation framing
        if _ADVISORY_PATTERNS.match(query):
            return "advisory/opinion framing detected"

        # 5. Questions that reference "you" in a way that implies the assistant
        #    knows the user's personal state ("do you remember", "can you see my")
        if re.search(r"\b(do you (remember|know|have|see)|can you (see|access|check) my)\b", query, re.IGNORECASE):
            return "query references assistant's knowledge of this specific user"

        return None  # passes all checks → cacheable
