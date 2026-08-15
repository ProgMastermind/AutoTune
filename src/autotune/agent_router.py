"""Deterministic routing policy for AutoTune's advisory OpenAI agents."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Mapping


class AgentRole(StrEnum):
    RESEARCH_TRIAGE = "research_triage"
    RESEARCH_SYNTHESIS = "research_synthesis"
    CANDIDATE_DESIGN = "candidate_design"
    CODE_CHANGE_PROPOSAL = "code_change_proposal"
    FAILURE_TRIAGE = "failure_triage"
    POLICY_CRITIC = "policy_critic"


_INSTRUCTIONS: dict[AgentRole, str] = {
    AgentRole.RESEARCH_TRIAGE: (
        "Extract atomic facts from the supplied material. Return evidence with sources and "
        "confidence. Do not invent compatibility claims, choose a Candidate, change source, "
        "or claim a performance result."
    ),
    AgentRole.RESEARCH_SYNTHESIS: (
        "Synthesize the supplied Model Dossier, Technique Catalog, profiler evidence, and "
        "experiment history into evidence-backed findings. Separate observed facts from "
        "hypotheses and identify missing evidence."
    ),
    AgentRole.CANDIDATE_DESIGN: (
        "Propose one bounded, reversible Candidate with its lane, preconditions, expected "
        "cost, risk, and measurement plan. Do not promote an Incumbent or execute a change."
    ),
    AgentRole.CODE_CHANGE_PROPOSAL: (
        "Produce a minimal draft patch plan for a verified bottleneck, including tests, "
        "allowed paths, rollback, and build checks. You must not claim promotion, modify a "
        "repository, or bypass source-mutation governance."
    ),
    AgentRole.FAILURE_TRIAGE: (
        "Classify the supplied failure from observed logs and artifacts. Return the most likely "
        "classification, confidence, retry safety, and the evidence that supports it."
    ),
    AgentRole.POLICY_CRITIC: (
        "Review a proposed Candidate for unsupported assumptions, budget risk, missing quality "
        "gates, and unsafe mutation scope. Return a concise accept, revise, or reject advisory."
    ),
}


@dataclass(frozen=True)
class AgentRouter:
    """Maps an advisory job to a model and non-authoritative system instruction."""

    research_model: str
    reasoning_model: str
    code_model: str

    @classmethod
    def from_environment(cls, environment: Mapping[str, str]) -> "AgentRouter":
        return cls(
            research_model=environment.get("AUTOTUNE_AGENT_RESEARCH_MODEL", "gpt-5.6-luna"),
            reasoning_model=environment.get("AUTOTUNE_AGENT_REASONING_MODEL", "gpt-5.6-terra"),
            code_model=environment.get("AUTOTUNE_AGENT_CODE_MODEL", "gpt-5.6-terra"),
        )

    def model_for(self, role: AgentRole) -> str:
        if role in {AgentRole.RESEARCH_TRIAGE, AgentRole.FAILURE_TRIAGE}:
            return self.research_model
        if role is AgentRole.CODE_CHANGE_PROPOSAL:
            return self.code_model
        return self.reasoning_model

    def build_request(self, role: AgentRole, input_text: str) -> dict[str, str]:
        """Build a serializable Responses API request without sending it."""
        return {
            "model": self.model_for(role),
            "role": role.value,
            "instructions": _INSTRUCTIONS[role],
            "input": input_text,
        }
