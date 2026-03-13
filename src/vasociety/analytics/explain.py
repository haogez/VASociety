"""Explanation builders for trace and metrics outputs."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any

from vasociety.analytics.trace_analyzer import (
    metrics_trace_consistency,
    persona_participation_summary,
    stance_shift_summary,
    top_diffusion_posts,
    topic_heat_over_time,
)
from vasociety.models.state import SimulationState


def _topic_peaks(heat_series: dict[str, list[dict[str, float | int]]]) -> list[dict[str, Any]]:
    peaks: list[dict[str, Any]] = []
    for topic, points in heat_series.items():
        if not points:
            continue
        peak = max(points, key=lambda item: float(item["heat"]))
        peaks.append({"topic": topic, "peak_step": int(peak["step"]), "peak_heat": float(peak["heat"])})
    peaks.sort(key=lambda item: item["peak_heat"], reverse=True)
    return peaks


def build_final_state_summary(state: SimulationState) -> dict[str, Any]:
    """Compact final-state summary for downstream analysis."""

    latest_metrics = asdict(state.metrics_history[-1]) if state.metrics_history else {}
    key_counts = {
        "total_agents": len(state.agents),
        "total_posts": len(state.posts),
        "total_comments": len(state.comments),
        "total_likes": sum(post.likes for post in state.posts.values()),
        "total_reposts": sum(post.reposts for post in state.posts.values()),
        "total_event_records": len(state.event_log),
        "total_decision_trace_records": len(state.decision_trace),
        "total_snapshots": len(state.snapshots),
    }
    social_summary = {
        "follow_edge_count": sum(len(edges) for edges in state.followees.values()),
        "trust_edge_count": sum(len(edges) for edges in state.trust_edges.values()),
        "community_count": len(set(state.community_labels.values())),
        "trending_pool_size": len(state.trending_pool),
        "official_pinned_content_size": len(state.official_pinned_content),
        "suppressed_content_size": len(state.suppressed_content),
    }
    per_agent_topic_stances = {
        agent_id: {
            "persona_type": agent.persona_type,
            "topic_stances": dict(agent.topic_stances),
            "stance_shift_count": sum(
                1
                for record in agent.stance_update_history
                if str(record.get("from", "")) != str(record.get("to", ""))
            ),
        }
        for agent_id, agent in state.agents.items()
    }
    heat_series = topic_heat_over_time(state)
    return {
        "run_id": state.run_id,
        "scenario_name": state.scenario_name,
        "current_step": state.current_step,
        "key_counts": key_counts,
        "latest_metrics": latest_metrics,
        "per_agent_topic_stances_summary": per_agent_topic_stances,
        "social_summary": social_summary,
        "topic_heat_peaks": _topic_peaks(heat_series)[:10],
    }


def generate_explanation_summary(state: SimulationState) -> dict[str, Any]:
    """Generate a richer explanation payload for papers and experiments."""

    heat_series = topic_heat_over_time(state)
    stance_summary = stance_shift_summary(state)
    persona_summary = persona_participation_summary(state)
    diffusion_summary = top_diffusion_posts(state, top_k=10)
    consistency = metrics_trace_consistency(state)

    return {
        "run_id": state.run_id,
        "scenario_name": state.scenario_name,
        "steps": state.current_step,
        "topic_heat_over_time": heat_series,
        "topic_heat_peaks": _topic_peaks(heat_series),
        "stance_shift_summary": stance_summary,
        "persona_participation_summary": persona_summary,
        "top_diffusion_posts": diffusion_summary,
        "metrics_trace_consistency": consistency,
    }
