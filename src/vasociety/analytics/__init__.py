"""Analytics and explainability utilities."""

from vasociety.analytics.explain import build_final_state_summary, generate_explanation_summary
from vasociety.analytics.trace_analyzer import (
    metrics_trace_consistency,
    persona_participation_summary,
    stance_shift_summary,
    top_diffusion_posts,
    topic_heat_over_time,
    validate_decision_trace_schema,
)

__all__ = [
    "build_final_state_summary",
    "generate_explanation_summary",
    "topic_heat_over_time",
    "stance_shift_summary",
    "persona_participation_summary",
    "top_diffusion_posts",
    "validate_decision_trace_schema",
    "metrics_trace_consistency",
]
