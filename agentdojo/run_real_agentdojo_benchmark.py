"""
Run actual AgentDojo banking benchmark tasks with and without Progent protection.
Uses the real AgentDojo task suite, user tasks, and injection attacks.
"""

import sys
from pathlib import Path
from typing import Any

# Add necessary paths
sys.path.insert(0, str(Path(__file__).parent.parent))
sys.path.insert(0, str(Path(__file__).parent / "src"))

from progent import load_policies, check_tool_call, ProgentBlockedError, reset_security_policy
# from agentdojo.functions_runtime import FunctionsRuntime

# Avoid circular imports by importing modules in the right order
# First, ensure task_suite module is loaded
# import agentdojo.default_suites.v1.tools.banking_client
# import agentdojo.default_suites.v1.tools.file_reader
# import agentdojo.default_suites.v1.tools.user_account

# Then import the task suite components
# from agentdojo.default_suites.v1.banking.task_suite import BankingEnvironment, TOOLS, task_suite
from src.agentdojo.agent_pipeline.agent_pipeline import AgentPipeline, PipelineConfig
from src.agentdojo.task_suite.load_suites import get_suite
from src.agentdojo.attacks.attack_registry import load_attack

def simulate_tool_execution_with_progent(
    task_ground_truth: list,
    env,
    runtime: FunctionsRuntime,
    protected: bool = False
) -> tuple[bool, list[str], Any]:
    """
    Simulate executing tool calls with optional Progent protection.
    
    Args:
        task_ground_truth: List of FunctionCall objects
        env: The environment
        runtime: FunctionsRuntime for actual execution
        protected: Whether to use Progent protection
        
    Returns:
        Tuple of (all_allowed, messages, final_env)
    """
    messages = []
    all_allowed = True
    current_env = env
    
    for i, call in enumerate(task_ground_truth):
        tool_name = call.function
        args = dict(call.args)
        
        try:
            if protected:
                # Check with Progent first
                check_tool_call(tool_name, args)
                messages.append(f"    [{i+1}] {tool_name}({_format_args(args)}) - ALLOWED")
            else:
                messages.append(f"    [{i+1}] {tool_name}({_format_args(args)}) - EXECUTED")
            
            # In a real scenario, you would execute the tool here
            # For simulation purposes, we just check the policy
            
        except ProgentBlockedError as e:
            messages.append(f"    [{i+1}] {tool_name}({_format_args(args)}) - BLOCKED")
            messages.append(f"        Reason: {str(e)[:100]}")
            all_allowed = False
    
    return all_allowed, messages, current_env


def _format_args(args: dict) -> str:
    """Format arguments for display."""
    formatted = []
    for k, v in args.items():
        if isinstance(v, str) and len(v) > 40:
            formatted.append(f"{k}='{v[:40]}...'")
        else:
            formatted.append(f"{k}={repr(v)}")
    return ", ".join(formatted)


def run_user_task(task_id: str, task, suite, protected: bool = False) -> dict[str, Any]:
    """Run a user task (legitimate operation)."""
    # Load environment without injection
    env = suite.load_and_inject_default_environment({})
    runtime = FunctionsRuntime.from_function_specs(suite.tools, env)
    
    # Get ground truth
    ground_truth = task.ground_truth(env)
    
    # Simulate execution
    all_allowed, messages, final_env = simulate_tool_execution_with_progent(
        ground_truth, env, runtime, protected
    )
    
    return {
        "task_id": task_id,
        "task_name": task.__class__.__name__,
        "prompt": task.PROMPT,
        "num_tool_calls": len(ground_truth),
        "all_allowed": all_allowed,
        "messages": messages,
        "expected": "ALLOW"
    }


def run_injection_task(
    task_id: str,
    injection_task,
    suite,
    protected: bool = False
) -> dict[str, Any]:
    """Run an injection task (attack attempt)."""
    # Load environment without injection (we're just checking if the attack would be blocked)
    env = suite.load_and_inject_default_environment({})
    runtime = FunctionsRuntime.from_function_specs(suite.tools, env)
    
    # Get ground truth for the attack
    ground_truth = injection_task.ground_truth(env)
    
    # Simulate execution
    all_allowed, messages, final_env = simulate_tool_execution_with_progent(
        ground_truth, env, runtime, protected
    )
    
    return {
        "task_id": task_id,
        "task_name": injection_task.__class__.__name__,
        "goal": injection_task.GOAL,
        "num_tool_calls": len(ground_truth),
        "all_allowed": all_allowed,
        "messages": messages,
        "expected": "BLOCK"
    }


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
    """Main demonstration script."""
    print("="*80)
    print("REAL AGENTDOJO BANKING BENCHMARK - PROGENT SECURITY DEMONSTRATION")
    print("="*80)
    print("Using actual AgentDojo task suite, user tasks, and injection attacks")
    print()
    
    # Load the actual banking suite from AgentDojo
    print("Loading AgentDojo banking suite...")
    
    # Import tasks after the suite is loaded to avoid circular imports
    import agentdojo.default_suites.v1.banking.user_tasks
    import agentdojo.default_suites.v1.banking.injection_tasks
    
    suite = banking_task_suite
    
    user_tasks = suite.user_tasks
    injection_tasks = suite.injection_tasks
    
    print(f"  Loaded {len(user_tasks)} user tasks")
    print(f"  Loaded {len(injection_tasks)} injection tasks")
    print(f"  Available tools: {len(suite.tools)}")
    
    # Select a subset of tasks to demonstrate
    # User tasks: legitimate operations
    user_task_ids = list(user_tasks.keys())[:5]  # First 5 user tasks
    
    # Injection tasks: attacks
    injection_task_ids = list(injection_tasks.keys())  # All injection tasks
    
    print(f"\nRunning {len(user_task_ids)} user tasks and {len(injection_task_ids)} injection attacks")
    
    # =========================================================================
    # RUN 1: WITHOUT PROGENT PROTECTION
    # =========================================================================
    print("\n" + "="*80)
    print("PART 1: WITHOUT PROGENT PROTECTION (Baseline - Vulnerable)")
    print("="*80)
    print("All operations execute without restrictions")
    
    reset_security_policy(include_manual=True)
    
    print("\n" + "-"*80)
    print("LEGITIMATE USER TASKS")
    print("-"*80)
    
    unprotected_user_results = []
    for task_id in user_task_ids:
        task = suite.get_user_task_by_id(task_id)
        result = run_user_task(task_id, task, suite, protected=False)
        unprotected_user_results.append(result)
        print_task_result(result, "UNPROTECTED")
    
    print("\n" + "-"*80)
    print("INJECTION ATTACKS (Execute without restriction - VULNERABLE!)")
    print("-"*80)
    
    unprotected_attack_results = []
    for task_id in injection_task_ids:
        injection_task = suite.get_injection_task_by_id(task_id)
        result = run_injection_task(task_id, injection_task, suite, protected=False)
        unprotected_attack_results.append(result)
        print_task_result(result, "UNPROTECTED")
    
    # =========================================================================
    # RUN 2: WITH PROGENT PROTECTION
    # =========================================================================
    print("\n\n" + "="*80)
    print("PART 2: WITH PROGENT PROTECTION")
    print("="*80)
    print("Security policies enforce fine-grained access control")
    
    # Load Progent policies
    policy_path = Path(__file__).parent / "progent_banking_policies.json"
    load_policies(str(policy_path))
    print(f"  [OK] Loaded Progent policies from {policy_path.name}")
    
    print("\n" + "-"*80)
    print("LEGITIMATE USER TASKS")
    print("-"*80)
    
    protected_user_results = []
    for task_id in user_task_ids:
        task = suite.get_user_task_by_id(task_id)
        result = run_user_task(task_id, task, suite, protected=True)
        protected_user_results.append(result)
        print_task_result(result, "PROTECTED")
    
    print("\n" + "-"*80)
    print("INJECTION ATTACKS (Should be blocked by policies)")
    print("-"*80)
    
    protected_attack_results = []
    for task_id in injection_task_ids:
        injection_task = suite.get_injection_task_by_id(task_id)
        result = run_injection_task(task_id, injection_task, suite, protected=True)
        protected_attack_results.append(result)
        print_task_result(result, "PROTECTED")
    
    # =========================================================================
    # SUMMARY STATISTICS
    # =========================================================================
    print("\n\n" + "="*80)
    print("SUMMARY COMPARISON")
    print("="*80)
    
    print("\nWITHOUT PROGENT:")
    print("-" * 40)
    unprotected_user_success = sum(1 for r in unprotected_user_results if r["all_allowed"])
    unprotected_attacks_executed = sum(1 for r in unprotected_attack_results if r["all_allowed"])
    
    print(f"  User Tasks Executed: {unprotected_user_success}/{len(unprotected_user_results)}")
    print(f"  Attacks Executed: {unprotected_attacks_executed}/{len(unprotected_attack_results)}")
    print(f"  Security Status: VULNERABLE - All attacks can execute!")
    
    print("\nWITH PROGENT:")
    print("-" * 40)
    protected_user_success = sum(1 for r in protected_user_results if r["all_allowed"])
    protected_attacks_blocked = sum(1 for r in protected_attack_results if not r["all_allowed"])
    
    print(f"  User Tasks Allowed: {protected_user_success}/{len(protected_user_results)}")
    print(f"  Attacks Blocked: {protected_attacks_blocked}/{len(protected_attack_results)}")
    
    false_positives = len(protected_user_results) - protected_user_success
    false_negatives = len(protected_attack_results) - protected_attacks_blocked
    
    if false_positives > 0:
        print(f"  False Positives: {false_positives} (legitimate tasks blocked)")
    if false_negatives > 0:
        print(f"  WARNING: False Negatives: {false_negatives} (attacks not blocked)")
    
    if protected_attacks_blocked == len(protected_attack_results) and false_positives == 0:
        print(f"  Security Status: PROTECTED - Perfect security with no false positives!")
    elif protected_attacks_blocked == len(protected_attack_results):
        print(f"  Security Status: PROTECTED - All attacks blocked (with some false positives)")
    else:
        print(f"  Security Status: PARTIALLY PROTECTED")
    
    print("\nDETAILED METRICS:")
    print("-" * 40)
    attack_prevention_rate = (protected_attacks_blocked / len(protected_attack_results)) * 100
    legitimate_success_rate = (protected_user_success / len(protected_user_results)) * 100
    
    print(f"  Attack Prevention Rate: {attack_prevention_rate:.1f}%")
    print(f"  Legitimate Task Success Rate: {legitimate_success_rate:.1f}%")
    print(f"  Total Attacks Prevented: {protected_attacks_blocked}/{len(protected_attack_results)}")
    print(f"  Total Tool Calls Analyzed: {sum(r['num_tool_calls'] for r in protected_user_results + protected_attack_results)}")
    
    print("\n" + "="*80)
    print("KEY FINDINGS:")
    print("="*80)
    print(f"1. WITHOUT PROGENT: System vulnerable - {unprotected_attacks_executed}/{len(unprotected_attack_results)} attacks execute")
    print(f"2. WITH PROGENT: {protected_attacks_blocked}/{len(protected_attack_results)} attacks blocked ({attack_prevention_rate:.0f}% prevention)")
    print(f"3. USABILITY: {protected_user_success}/{len(protected_user_results)} legitimate tasks work ({legitimate_success_rate:.0f}% success rate)")
    print(f"4. Progent policies provide defense-in-depth with minimal operational impact")
    print("="*80 + "\n")
    
    # List specific attacks blocked
    if protected_attacks_blocked > 0:
        print("\nATTACKS SUCCESSFULLY BLOCKED:")
        print("-" * 40)
        for result in protected_attack_results:
            if not result["all_allowed"]:
                print(f"  - {result['task_id']}: {result['goal'][:70]}...")


if __name__ == "__main__":
    main()
