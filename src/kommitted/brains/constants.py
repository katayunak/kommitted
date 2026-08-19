"""Constants shared by every brain, and the LLM brain's settings."""

# An LLM answer is trusted only above this. Below it we fall back to rules -
# a confidently wrong model is worse than an honest heuristic.
LLM_MIN_CONFIDENCE = 0.4

REASON_LLM_PREFIX = "model: "
REASON_LLM_FALLBACK = "LLM unavailable ({error}) - fell back to rules"
REASON_LLM_LOW_CONFIDENCE = "model confidence {value:.2f} below threshold - used rules"

# Model names are configuration, not constants - Google retires them on
# their own schedule. Override with KOMMITTED_MODEL rather than editing here.
GEMINI_MODEL = "gemini-3.6-flash"
GEMINI_API_URL = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
GEMINI_API_KEY_ENV = "GEMINI_API_KEY"
LLM_TIMEOUT_SECONDS = 20

# Diffs can be enormous. Truncate before sending: free tiers have token
# limits, and the first N lines carry most of the signal anyway.
MAX_DIFF_CHARS = 12000
