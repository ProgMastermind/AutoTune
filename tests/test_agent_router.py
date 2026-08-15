import os
from pathlib import Path
import sys
import unittest


sys.path.insert(0, str(Path(__file__).parents[1] / "src"))

from autotune.agent_router import AgentRole, AgentRouter


class AgentRouterTests(unittest.TestCase):
    def test_routes_high_volume_research_triage_to_luna(self) -> None:
        router = AgentRouter.from_environment(
            {
                "AUTOTUNE_AGENT_RESEARCH_MODEL": "gpt-5.6-luna",
                "AUTOTUNE_AGENT_REASONING_MODEL": "gpt-5.6-terra",
                "AUTOTUNE_AGENT_CODE_MODEL": "gpt-5.6-terra",
            }
        )

        request = router.build_request(
            AgentRole.RESEARCH_TRIAGE,
            "Extract model and runtime facts from this profile summary.",
        )

        self.assertEqual(request["model"], "gpt-5.6-luna")
        self.assertEqual(request["role"], "research_triage")
        self.assertIn("Return evidence with sources and confidence", request["instructions"])

    def test_routes_code_change_proposals_to_terra_without_promotion_authority(self) -> None:
        router = AgentRouter.from_environment(
            {
                "AUTOTUNE_AGENT_RESEARCH_MODEL": "gpt-5.6-luna",
                "AUTOTUNE_AGENT_REASONING_MODEL": "gpt-5.6-terra",
                "AUTOTUNE_AGENT_CODE_MODEL": "gpt-5.6-terra",
            }
        )

        request = router.build_request(
            AgentRole.CODE_CHANGE_PROPOSAL,
            "Propose a minimal patch for the verified kernel-dispatch bottleneck.",
        )

        self.assertEqual(request["model"], "gpt-5.6-terra")
        self.assertEqual(request["role"], "code_change_proposal")
        self.assertIn("must not claim promotion", request["instructions"])
        self.assertIn("draft patch plan", request["instructions"])

    def test_defaults_preserve_the_luna_and_terra_operating_model(self) -> None:
        router = AgentRouter.from_environment({})

        self.assertEqual(router.model_for(AgentRole.RESEARCH_TRIAGE), "gpt-5.6-luna")
        self.assertEqual(router.model_for(AgentRole.RESEARCH_SYNTHESIS), "gpt-5.6-terra")
        self.assertEqual(router.model_for(AgentRole.CODE_CHANGE_PROPOSAL), "gpt-5.6-terra")


if __name__ == "__main__":
    unittest.main()
