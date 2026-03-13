"""Layered runtime state models: world, artifacts, and runtime metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from vasociety.models.agent import ActionRecord, Agent
from vasociety.models.content import Comment, Post
from vasociety.models.ids import IdCounters
from vasociety.models.intervention import Intervention
from vasociety.models.metrics import MetricsSnapshot


@dataclass(slots=True)
class WorldState:
    current_step: int = 0
    agents: dict[str, Agent] = field(default_factory=dict)
    posts: dict[str, Post] = field(default_factory=dict)
    comments: dict[str, Comment] = field(default_factory=dict)
    stance_shift_count: int = 0
    followees: dict[str, list[str]] = field(default_factory=dict)
    followers: dict[str, list[str]] = field(default_factory=dict)
    trust_edges: dict[str, dict[str, float]] = field(default_factory=dict)
    affinity_edges: dict[str, dict[str, float]] = field(default_factory=dict)
    community_labels: dict[str, str] = field(default_factory=dict)
    trending_pool: list[str] = field(default_factory=list)
    official_pinned_content: list[str] = field(default_factory=list)
    suppressed_content: list[str] = field(default_factory=list)

    @property
    def follow_graph(self) -> dict[str, list[str]]:
        return self.followees

    @property
    def trust_graph(self) -> dict[str, dict[str, float]]:
        return self.trust_edges

    def to_dict(self) -> dict[str, Any]:
        return {
            "current_step": self.current_step,
            "agents": {agent_id: _serialize_agent(agent) for agent_id, agent in self.agents.items()},
            "posts": {post_id: asdict(post) for post_id, post in self.posts.items()},
            "comments": {comment_id: asdict(comment) for comment_id, comment in self.comments.items()},
            "stance_shift_count": self.stance_shift_count,
            "followees": {agent_id: list(neighbors) for agent_id, neighbors in self.followees.items()},
            "followers": {agent_id: list(neighbors) for agent_id, neighbors in self.followers.items()},
            "trust_edges": {
                src_id: {dst_id: float(weight) for dst_id, weight in edges.items()}
                for src_id, edges in self.trust_edges.items()
            },
            "affinity_edges": {
                src_id: {dst_id: float(weight) for dst_id, weight in edges.items()}
                for src_id, edges in self.affinity_edges.items()
            },
            "community_labels": dict(self.community_labels),
            "trending_pool": list(self.trending_pool),
            "official_pinned_content": list(self.official_pinned_content),
            "suppressed_content": list(self.suppressed_content),
            # Backward-compatible keys for older outputs.
            "follow_graph": {agent_id: list(neighbors) for agent_id, neighbors in self.followees.items()},
            "trust_graph": {
                src_id: {dst_id: float(weight) for dst_id, weight in edges.items()}
                for src_id, edges in self.trust_edges.items()
            },
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> WorldState:
        agents_raw = _as_mapping(payload.get("agents", {}))
        posts_raw = _as_mapping(payload.get("posts", {}))
        comments_raw = _as_mapping(payload.get("comments", {}))
        followees_raw = _as_mapping(payload.get("followees", payload.get("follow_graph", {})))
        followers_raw = _as_mapping(payload.get("followers", {}))
        trust_edges_raw = _as_mapping(payload.get("trust_edges", payload.get("trust_graph", {})))
        affinity_edges_raw = _as_mapping(payload.get("affinity_edges", {}))
        community_labels_raw = _as_mapping(payload.get("community_labels", {}))
        trending_pool_raw = _as_list(payload.get("trending_pool", []))
        pinned_raw = _as_list(payload.get("official_pinned_content", []))
        suppressed_raw = _as_list(payload.get("suppressed_content", []))
        followees = {agent_id: [str(value) for value in values] for agent_id, values in followees_raw.items()}
        followers = {agent_id: [str(value) for value in values] for agent_id, values in followers_raw.items()}
        if not followers and followees:
            followers = {agent_id: [] for agent_id in followees}
            for src_id, targets in followees.items():
                for dst_id in targets:
                    followers.setdefault(dst_id, []).append(src_id)
        return cls(
            current_step=int(payload.get("current_step", 0)),
            agents={agent_id: _deserialize_agent(raw) for agent_id, raw in agents_raw.items()},
            posts={post_id: Post(**raw) for post_id, raw in posts_raw.items()},
            comments={comment_id: Comment(**raw) for comment_id, raw in comments_raw.items()},
            stance_shift_count=int(payload.get("stance_shift_count", 0)),
            followees=followees,
            followers=followers,
            trust_edges={
                src_id: {dst_id: float(weight) for dst_id, weight in _as_mapping(edges).items()}
                for src_id, edges in trust_edges_raw.items()
            },
            affinity_edges={
                src_id: {dst_id: float(weight) for dst_id, weight in _as_mapping(edges).items()}
                for src_id, edges in affinity_edges_raw.items()
            },
            community_labels={agent_id: str(label) for agent_id, label in community_labels_raw.items()},
            trending_pool=[str(item) for item in trending_pool_raw],
            official_pinned_content=[str(item) for item in pinned_raw],
            suppressed_content=[str(item) for item in suppressed_raw],
        )


@dataclass(slots=True)
class RunArtifacts:
    metrics_history: list[MetricsSnapshot] = field(default_factory=list)
    event_log: list[dict[str, Any]] = field(default_factory=list)
    snapshots: list[dict[str, Any]] = field(default_factory=list)
    decision_trace: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "metrics_history": [asdict(metric) for metric in self.metrics_history],
            "event_log": [dict(item) for item in self.event_log],
            "snapshots": [dict(item) for item in self.snapshots],
            "decision_trace": [dict(item) for item in self.decision_trace],
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RunArtifacts:
        return cls(
            metrics_history=[MetricsSnapshot(**item) for item in _as_list(payload.get("metrics_history", []))],
            event_log=[dict(item) for item in _as_list(payload.get("event_log", []))],
            snapshots=[dict(item) for item in _as_list(payload.get("snapshots", []))],
            decision_trace=[dict(item) for item in _as_list(payload.get("decision_trace", []))],
        )


@dataclass(slots=True, init=False)
class RuntimeState:
    run_id: str
    scenario_name: str
    world_state: WorldState
    run_artifacts: RunArtifacts
    interventions: list[Intervention]
    id_counters: IdCounters

    def __init__(
        self,
        current_step: int = 0,
        agents: dict[str, Agent] | None = None,
        posts: dict[str, Post] | None = None,
        comments: dict[str, Comment] | None = None,
        interventions: list[Intervention] | None = None,
        metrics_history: list[MetricsSnapshot] | None = None,
        event_log: list[dict[str, Any]] | None = None,
        snapshots: list[dict[str, Any]] | None = None,
        decision_trace: list[dict[str, Any]] | None = None,
        stance_shift_count: int = 0,
        follow_graph: dict[str, list[str]] | None = None,
        trust_graph: dict[str, dict[str, float]] | None = None,
        followees: dict[str, list[str]] | None = None,
        followers: dict[str, list[str]] | None = None,
        trust_edges: dict[str, dict[str, float]] | None = None,
        affinity_edges: dict[str, dict[str, float]] | None = None,
        community_labels: dict[str, str] | None = None,
        trending_pool: list[str] | None = None,
        official_pinned_content: list[str] | None = None,
        suppressed_content: list[str] | None = None,
        run_id: str = "run_00001",
        scenario_name: str = "default_scenario",
        world_state: WorldState | None = None,
        run_artifacts: RunArtifacts | None = None,
    ) -> None:
        if world_state is None:
            world_state = WorldState(
                current_step=current_step,
                agents=dict(agents or {}),
                posts=dict(posts or {}),
                comments=dict(comments or {}),
                stance_shift_count=stance_shift_count,
                followees={
                    agent_id: list(edges)
                    for agent_id, edges in ((followees if followees is not None else follow_graph) or {}).items()
                },
                followers={agent_id: list(edges) for agent_id, edges in (followers or {}).items()},
                trust_edges={
                    src_id: {dst_id: float(weight) for dst_id, weight in edges.items()}
                    for src_id, edges in ((trust_edges if trust_edges is not None else trust_graph) or {}).items()
                },
                affinity_edges={
                    src_id: {dst_id: float(weight) for dst_id, weight in edges.items()}
                    for src_id, edges in (affinity_edges or {}).items()
                },
                community_labels={agent_id: str(label) for agent_id, label in (community_labels or {}).items()},
                trending_pool=[str(item) for item in (trending_pool or [])],
                official_pinned_content=[str(item) for item in (official_pinned_content or [])],
                suppressed_content=[str(item) for item in (suppressed_content or [])],
            )
        if run_artifacts is None:
            run_artifacts = RunArtifacts(
                metrics_history=list(metrics_history or []),
                event_log=[dict(item) for item in (event_log or [])],
                snapshots=[dict(item) for item in (snapshots or [])],
                decision_trace=[dict(item) for item in (decision_trace or [])],
            )
        self.run_id = str(run_id)
        self.scenario_name = str(scenario_name)
        self.world_state = world_state
        self.run_artifacts = run_artifacts
        self.interventions = list(interventions or [])
        self.id_counters = IdCounters()
        self.id_counters.sync(post_ids=self.world_state.posts.keys(), comment_ids=self.world_state.comments.keys())

    @property
    def current_step(self) -> int:
        return self.world_state.current_step

    @current_step.setter
    def current_step(self, value: int) -> None:
        self.world_state.current_step = int(value)

    @property
    def agents(self) -> dict[str, Agent]:
        return self.world_state.agents

    @property
    def posts(self) -> dict[str, Post]:
        return self.world_state.posts

    @property
    def comments(self) -> dict[str, Comment]:
        return self.world_state.comments

    @property
    def stance_shift_count(self) -> int:
        return self.world_state.stance_shift_count

    @stance_shift_count.setter
    def stance_shift_count(self, value: int) -> None:
        self.world_state.stance_shift_count = int(value)

    @property
    def follow_graph(self) -> dict[str, list[str]]:
        return self.world_state.followees

    @property
    def trust_graph(self) -> dict[str, dict[str, float]]:
        return self.world_state.trust_edges

    @property
    def followees(self) -> dict[str, list[str]]:
        return self.world_state.followees

    @property
    def followers(self) -> dict[str, list[str]]:
        return self.world_state.followers

    @property
    def trust_edges(self) -> dict[str, dict[str, float]]:
        return self.world_state.trust_edges

    @property
    def affinity_edges(self) -> dict[str, dict[str, float]]:
        return self.world_state.affinity_edges

    @property
    def community_labels(self) -> dict[str, str]:
        return self.world_state.community_labels

    @property
    def trending_pool(self) -> list[str]:
        return self.world_state.trending_pool

    @property
    def official_pinned_content(self) -> list[str]:
        return self.world_state.official_pinned_content

    @property
    def suppressed_content(self) -> list[str]:
        return self.world_state.suppressed_content

    @property
    def metrics_history(self) -> list[MetricsSnapshot]:
        return self.run_artifacts.metrics_history

    @property
    def event_log(self) -> list[dict[str, Any]]:
        return self.run_artifacts.event_log

    @property
    def snapshots(self) -> list[dict[str, Any]]:
        return self.run_artifacts.snapshots

    @property
    def decision_trace(self) -> list[dict[str, Any]]:
        return self.run_artifacts.decision_trace

    def next_post_id(self) -> str:
        return self.id_counters.allocate_post_id()

    def next_comment_id(self) -> str:
        return self.id_counters.allocate_comment_id()

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "scenario_name": self.scenario_name,
            "interventions": [asdict(item) for item in self.interventions],
            "world_state": self.world_state.to_dict(),
            "run_artifacts": self.run_artifacts.to_dict(),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> RuntimeState:
        interventions_raw = _as_list(payload.get("interventions", []))
        return cls(
            run_id=str(payload.get("run_id", "run_00001")),
            scenario_name=str(payload.get("scenario_name", "default_scenario")),
            interventions=[Intervention(**raw) for raw in interventions_raw],
            world_state=WorldState.from_dict(_as_mapping(payload.get("world_state", {}))),
            run_artifacts=RunArtifacts.from_dict(_as_mapping(payload.get("run_artifacts", {}))),
        )


class SimulationState(RuntimeState):
    """Backward-compatible name for runtime state."""


def _as_mapping(raw: Any) -> dict[str, Any]:
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError("Expected mapping value")
    return dict(raw)


def _as_list(raw: Any) -> list[Any]:
    if raw is None:
        return []
    if not isinstance(raw, list):
        raise ValueError("Expected list value")
    return list(raw)


def _serialize_agent(agent: Agent) -> dict[str, Any]:
    payload = asdict(agent)
    payload["seen_content_ids"] = sorted(agent.seen_content_ids)
    return payload


def _deserialize_agent(payload: dict[str, Any]) -> Agent:
    data = dict(payload)
    action_history_raw = _as_list(data.get("action_history", []))
    data["action_history"] = [ActionRecord(**record) for record in action_history_raw]
    seen_content_ids = set(str(item) for item in _as_list(data.get("seen_content_ids", [])))
    data["seen_content_ids"] = seen_content_ids
    return Agent(**data)
