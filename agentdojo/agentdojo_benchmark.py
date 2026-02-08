from pathlib import Path

from dotenv import load_dotenv
from progent import reset_security_policy

# Load environment variables
load_dotenv()

from agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
from agentdojo.task_suite.load_suites import get_suite

# def run_user_task(task_id: str, task, suite, protected: bool = False) -> dict[str, Any]:
#     """Run a user task (legitimate operation)."""
#     # Load environment without injection
#     env = suite.load_and_inject_default_environment({})
#     runtime = FunctionsRuntime.from_function_specs(suite.tools, env)

#     # Get ground truth
#     ground_truth = task.ground_truth(env)

#     # Simulate execution
#     all_allowed, messages, final_env = simulate_tool_execution_with_progent(
#         ground_truth, env, runtime, protected
#     )


#     return {
#         "task_id": task_id,
#         "task_name": task.__class__.__name__,
#         "prompt": task.PROMPT,
#         "num_tool_calls": len(ground_truth),
#         "all_allowed": all_allowed,
#         "messages": messages,
#         "expected": "ALLOW"
#     }
def print_task_result(result: dict, mode: str):
    """Print task result in a formatted way."""
    print(f"\n[{result['task_id']}] {result['task_name']}:")

    if "prompt" in result:
        print(f"  User Request: {result['prompt']}")
    elif "goal" in result:
        print(f"  Attack Goal: {result['goal']}")

    print(f"  Tool Calls: {result['num_tool_calls']}")

    expected = result["expected"]
    all_allowed = result["all_allowed"]

    if mode == "UNPROTECTED":
        # Unprotected always allows everything
        status = "[ALL EXECUTED]"
        if expected == "BLOCK":
            verdict = "[VULNERABLE TO ATTACK]"
        else:
            verdict = "[OK]"
    else:
        # Protected mode
        if expected == "ALLOW" and all_allowed:
            verdict = "[OK - All Allowed]"
            status = "[EXECUTED]"
        elif expected == "ALLOW" and not all_allowed:
            verdict = "[FALSE POSITIVE - Some Blocked]"
            status = "[PARTIALLY BLOCKED]"
        elif expected == "BLOCK" and not all_allowed:
            verdict = "[OK - Attack Blocked]"
            status = "[BLOCKED]"
        else:  # expected == "BLOCK" and all_allowed
            verdict = "[FALSE NEGATIVE - Attack Allowed]"
            status = "[EXECUTED]"

    print(f"  Result: {status} {verdict}")

    # Print tool call details
    for msg in result["messages"]:
        print(msg)


def main():
    print("\n" + "=" * 100)
    print("⚔️  AGENTDOJO BANKING SUITE - INJECTION ATTACK DEMONSTRATION")
    print("=" * 100)
    print("\nThis script demonstrates how prompt injection attacks work in AgentDojo.")
    print("You'll see how malicious instructions are injected into the environment")
    print("and how the system evaluates whether the agent was compromised.\n")

    # Configuration
    model = "gpt-4.1-mini-2024-07-18"
    suite_name = "banking"
    benchmark_version = "v1"
    attack_name = "important_instructions"  # A common injection attack
    logdir = Path("./my_attack_demo")

    print("📋 Configuration:")
    print(f"   Model: {model}")
    print(f"   Suite: {suite_name}")
    print(f"   Benchmark Version: {benchmark_version}")
    print(f"   Attack: {attack_name}")
    print(f"   Log Directory: {logdir}")
    print()

    # Load the banking suite
    print("🔍 Loading banking suite...")
    suite = get_suite(benchmark_version, suite_name)
    print(f"✓ Suite loaded: {suite.name}")
    print(f"   Available tools: {[tool.name for tool in suite.tools]}")
    print(f"   User tasks: {list(suite.user_tasks.keys())[:3]}...")
    print(f"   Injection tasks: {list(suite.injection_tasks.keys())[:3]}...")
    print()

    # Create the agent pipeline
    print("🏗️  Creating agent pipeline...")
    pipeline = AgentPipeline.from_config(
        PipelineConfig(
            llm=model,
            model_id=None,
            defense=None,  # No defense - let's see the attack work!
            system_message_name=None,
            system_message=None,
            tool_output_format="json",
        )
    )
    print(f"✓ Pipeline created: {pipeline.name}")
    print("   Defense: None (vulnerable to attacks)")
    print()

    user_tasks = suite.user_tasks
    injection_tasks = suite.injection_tasks

    print(f"  Loaded {len(user_tasks)} user tasks")
    print(f"  Loaded {len(injection_tasks)} injection tasks")
    print(f"  Available tools: {len(suite.tools)}")

    # Select a subset of tasks to demonstrate
    # User tasks: legitimate operations
    user_task_ids = list(user_tasks.keys())[:2]  # First 5 user tasks

    # Injection tasks: attacks
    injection_task_ids = list(injection_tasks.keys())[:2]  # All injection tasks

    print(f"\nRunning {len(user_task_ids)} user tasks and {len(injection_task_ids)} injection attacks")

    # =========================================================================
    # RUN 1: WITHOUT PROGENT PROTECTION
    # =========================================================================
    print("\n" + "=" * 80)
    print("PART 1: WITHOUT PROGENT PROTECTION (Baseline - Vulnerable)")
    print("=" * 80)
    print("All operations execute without restrictions")

    reset_security_policy(include_manual=True)

    print("\n" + "-" * 80)
    print("LEGITIMATE USER TASKS")
    print("-" * 80)

    for task_id in user_task_ids:
        task = suite.get_user_task_by_id(task_id)
        print(f"Task: {task}")
        # result = run_user_task(task_id, task, suite, protected=False)
        # unprotected_user_results.append(result)
        # print_task_result(result, "UNPROTECTED")

    # Load the attack
    # print(f"⚔️  Loading attack: {attack_name}")
    # attacker = load_attack(attack_name, suite, pipeline)
    # print(f"✓ Attack loaded: {attacker.__class__.__name__}")
    # print(f"   Attack type: {attacker.name}")
    # print(f"   Is DoS attack: {attacker.is_dos_attack}")
    # print()


if __name__ == "__main__":
    main()
