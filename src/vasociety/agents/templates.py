"""Persona templates used to instantiate agents."""

from __future__ import annotations

PERSONA_TEMPLATES: dict[str, dict[str, float]] = {
    "rational_checker": {
        "activity_profile": 0.55,
        "expression_level": 0.45,
        "conformity_level": 0.25,
        "skepticism_level": 0.8,
        "emotionality_level": 0.2,
        "authority_trust_level": 0.55,
    },
    "emotional_reactor": {
        "activity_profile": 0.7,
        "expression_level": 0.85,
        "conformity_level": 0.35,
        "skepticism_level": 0.3,
        "emotionality_level": 0.9,
        "authority_trust_level": 0.35,
    },
    "herd_follower": {
        "activity_profile": 0.6,
        "expression_level": 0.5,
        "conformity_level": 0.85,
        "skepticism_level": 0.25,
        "emotionality_level": 0.5,
        "authority_trust_level": 0.45,
    },
    "silent_observer": {
        "activity_profile": 0.35,
        "expression_level": 0.15,
        "conformity_level": 0.4,
        "skepticism_level": 0.55,
        "emotionality_level": 0.3,
        "authority_trust_level": 0.5,
    },
    "expressive_speaker": {
        "activity_profile": 0.8,
        "expression_level": 0.95,
        "conformity_level": 0.3,
        "skepticism_level": 0.35,
        "emotionality_level": 0.65,
        "authority_trust_level": 0.4,
    },
    "authority_truster": {
        "activity_profile": 0.5,
        "expression_level": 0.4,
        "conformity_level": 0.6,
        "skepticism_level": 0.2,
        "emotionality_level": 0.35,
        "authority_trust_level": 0.9,
    },
}
