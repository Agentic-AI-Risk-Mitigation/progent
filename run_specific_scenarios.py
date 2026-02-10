"""Run individual scenarios for debugging."""

import sys

from implementations.evals.harness import Evaluator
from implementations.evals.scenarios import SCENARIOS

# Get scenario names from command line or default to failing ones
if len(sys.argv) > 1:
    scenario_names = sys.argv[1:]
else:
    scenario_names = ["A1_DataAnalysis", "C1_RecursiveDelete", "C3_Typosquatting"]

# Filter scenarios
scenarios_to_run = [s for s in SCENARIOS if s.name in scenario_names]

if not scenarios_to_run:
    print(f"No scenarios found matching: {scenario_names}")
    sys.exit(1)

# Run scenarios
evaluator = Evaluator(policy_path="implementations/evals/eval_policies.json")

for scenario in scenarios_to_run:
    print("\n" + "=" * 80)
    result = evaluator.run_scenario(scenario)
    print(f"\nRESULT: {result['status']}")
    print(f"Expected: {result['details']}")
    if "blocked_tools" in result:
        print(f"Blocked tools: {result['blocked_tools']}")
        print(f"Allowed tools: {result['allowed_tools']}")
    print("=" * 80)

# Summary
evaluator.generate_report()
