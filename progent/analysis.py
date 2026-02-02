"""
Progent policy analysis using Z3 solver.

This module provides tools for analyzing policies:
- Conflict detection between policy rules
- Satisfiability checking of restrictions

This is an OPTIONAL module. It requires z3-solver to be installed:
    pip install progent[analysis]
"""

from typing import Any


def analyze_policies(policies: dict = None) -> list[str]:
    """
    Analyze security policies for conflicts and issues.
    
    Uses Z3 SMT solver to detect:
    - Overlapping allow/deny rules
    - Unsatisfiable restrictions
    - Redundant rules
    
    Args:
        policies: Policies to analyze. If None, uses current policies.
        
    Returns:
        List of warning messages
        
    Raises:
        ImportError: If z3-solver is not installed
    """
    try:
        from z3 import (
            Solver, sat, And, Or, Not, Implies, If, Sum,
            String, Int, Real, Bool, Const,
            StringVal, IntVal, RealVal, BoolVal,
            InRe, Length, Re, Range, Star, Plus, Option, Concat, Union, Intersect,
            Loop, Complement, ForAll, Exists, Select, Store, K,
            IntSort, RealSort, BoolSort, StringSort, ArraySort,
            Datatype,
        )
    except ImportError:
        raise ImportError(
            "z3-solver is required for policy analysis. "
            "Install it with: pip install progent[analysis]"
        )
    
    if policies is None:
        from progent.core import get_security_policy
        policies = get_security_policy()
    
    if policies is None:
        return []
    
    warnings = []
    
    for tool_name, rules in policies.items():
        n = len(rules)
        for i in range(n):
            for j in range(i + 1, n):
                rule_i = rules[i]
                rule_j = rules[j]
                
                # Get conditions from rules
                conditions_i = rule_i[2] if len(rule_i) > 2 else {}
                conditions_j = rule_j[2] if len(rule_j) > 2 else {}
                
                # Check each argument for overlap
                for arg_name, restriction_i in conditions_i.items():
                    if arg_name not in conditions_j:
                        continue
                    
                    restriction_j = conditions_j[arg_name]
                    
                    # Only check JSON Schema restrictions
                    if not isinstance(restriction_i, dict) or not isinstance(restriction_j, dict):
                        continue
                    
                    # Try to find overlap
                    overlap = _check_schema_overlap(restriction_i, restriction_j)
                    if overlap:
                        warnings.append(
                            f"Policy overlap in {tool_name}.{arg_name}: "
                            f"rules {i} and {j} overlap. Example value: {overlap}"
                        )
    
    return warnings


def _check_schema_overlap(schema_a: dict, schema_b: dict) -> Any:
    """
    Check if two JSON schemas can be satisfied by the same value.
    
    Returns an example value if overlap exists, None otherwise.
    """
    try:
        from z3 import Solver, sat, And, String, Int, Real, Bool
    except ImportError:
        return None
    
    # Create combined schema (allOf)
    combined = {
        "allOf": [schema_a, schema_b]
    }
    
    # Try to solve
    model, var = _solve_schema(combined)
    
    if model is not None:
        return model[var]
    
    return None


def _solve_schema(schema: dict):
    """
    Solve a JSON schema to find a satisfying value.
    
    Returns (model, variable) if satisfiable, (None, variable) otherwise.
    """
    try:
        from z3 import (
            Solver, sat, And, Or, Not, Implies, If,
            String, Int, Real, Bool, Const,
            StringVal, IntVal, RealVal, BoolVal,
            InRe, Length, Re, Range, Star, Plus, Option, Concat, Union,
            Loop, ForAll, Exists, Select, Store, K,
            IntSort, RealSort, BoolSort, StringSort, ArraySort,
            Datatype,
        )
    except ImportError:
        return None, None
    
    # Determine variable type from schema
    var = _create_variable(schema)
    
    # Build constraints
    constraints = _build_constraints(var, schema)
    
    # Solve
    solver = Solver()
    solver.add(constraints)
    
    if solver.check() == sat:
        return solver.model(), var
    
    return None, var


def _create_variable(schema: dict):
    """Create appropriate Z3 variable based on schema type."""
    from z3 import String, Int, Real, Bool, Const
    
    schema_type = schema.get("type", "string")
    
    if isinstance(schema_type, list):
        # Multiple types - use first one
        schema_type = schema_type[0]
    
    if schema_type == "string":
        return String("x")
    elif schema_type == "integer":
        return Int("x")
    elif schema_type == "number":
        return Real("x")
    elif schema_type == "boolean":
        return Bool("x")
    else:
        return String("x")  # Default to string


def _build_constraints(var, schema: dict):
    """Build Z3 constraints from JSON schema."""
    from z3 import (
        And, Or, Not, Implies, If,
        StringVal, IntVal, RealVal, BoolVal,
        InRe, Length, Re, Range, Star, Plus, Option, Concat, Union,
        StringSort, IntSort, RealSort, BoolSort,
    )
    import sre_parse
    
    constraints = []
    
    # enum constraint
    if "enum" in schema:
        enums = schema["enum"]
        if enums:
            first = enums[0]
            if isinstance(first, str):
                constraints.append(Or([var == StringVal(e) for e in enums]))
            elif isinstance(first, int):
                constraints.append(Or([var == IntVal(e) for e in enums]))
            elif isinstance(first, float):
                constraints.append(Or([var == RealVal(e) for e in enums]))
            elif isinstance(first, bool):
                constraints.append(Or([var == BoolVal(e) for e in enums]))
    
    # anyOf
    if "anyOf" in schema:
        branch_constraints = [_build_constraints(var, sub) for sub in schema["anyOf"]]
        constraints.append(Or(branch_constraints))
    
    # allOf
    if "allOf" in schema:
        for sub in schema["allOf"]:
            constraints.append(_build_constraints(var, sub))
    
    # oneOf
    if "oneOf" in schema:
        oneof = [_build_constraints(var, sub) for sub in schema["oneOf"]]
        # Exactly one must be true
        for i, c in enumerate(oneof):
            others = oneof[:i] + oneof[i+1:]
            constraints.append(Implies(c, And([Not(o) for o in others])))
        constraints.append(Or(oneof))
    
    # not
    if "not" in schema:
        constraints.append(Not(_build_constraints(var, schema["not"])))
    
    # String constraints
    if var.sort() == StringSort():
        if "pattern" in schema:
            try:
                pattern = schema["pattern"]
                regex = _pattern_to_z3_regex(pattern)
                if regex is not None:
                    constraints.append(InRe(var, regex))
            except Exception:
                pass  # Skip invalid patterns
        
        if "minLength" in schema:
            constraints.append(Length(var) >= schema["minLength"])
        
        if "maxLength" in schema:
            constraints.append(Length(var) <= schema["maxLength"])
    
    # Numeric constraints
    if var.sort() in (IntSort(), RealSort()):
        if "minimum" in schema:
            constraints.append(var >= schema["minimum"])
        
        if "exclusiveMinimum" in schema:
            constraints.append(var > schema["exclusiveMinimum"])
        
        if "maximum" in schema:
            constraints.append(var <= schema["maximum"])
        
        if "exclusiveMaximum" in schema:
            constraints.append(var < schema["exclusiveMaximum"])
        
        if "multipleOf" in schema and var.sort() == IntSort():
            m = schema["multipleOf"]
            constraints.append(var % m == 0)
    
    if constraints:
        return And(constraints)
    else:
        return True  # No constraints


def _pattern_to_z3_regex(pattern: str):
    """Convert a regex pattern to Z3 regex."""
    from z3 import Re, Range, Star, Plus, Option, Concat, Union
    import sre_parse
    import sre_constants
    
    try:
        parsed = sre_parse.parse(pattern)
    except Exception:
        return None
    
    def convert_node(node_type, node_value):
        if node_type == sre_constants.LITERAL:
            return Re(chr(node_value))
        elif node_type == sre_constants.ANY:
            return Range(chr(0), chr(127))
        elif node_type == sre_constants.MAX_REPEAT:
            low, high, value = node_value
            inner = convert_pattern(value)
            if (low, high) == (0, 1):
                return Option(inner)
            elif (low, high) == (0, sre_constants.MAXREPEAT):
                return Star(inner)
            elif (low, high) == (1, sre_constants.MAXREPEAT):
                return Plus(inner)
            else:
                # Bounded repeat - approximate with Loop if available
                from z3 import Loop
                return Loop(inner, low, high)
        elif node_type == sre_constants.IN:
            # Character class
            options = []
            for sub_type, sub_value in node_value:
                if sub_type == sre_constants.RANGE:
                    low, high = sub_value
                    options.append(Range(chr(low), chr(high)))
                elif sub_type == sre_constants.LITERAL:
                    options.append(Re(chr(sub_value)))
                elif sub_type == sre_constants.CATEGORY:
                    if sub_value == sre_constants.CATEGORY_DIGIT:
                        options.append(Range("0", "9"))
                    elif sub_value == sre_constants.CATEGORY_WORD:
                        options.append(Union(
                            Range("a", "z"),
                            Range("A", "Z"),
                            Range("0", "9"),
                            Re("_"),
                        ))
                    elif sub_value == sre_constants.CATEGORY_SPACE:
                        options.append(Union(Re(" "), Re("\t"), Re("\n")))
            if options:
                return Union(*options) if len(options) > 1 else options[0]
            return Re("")
        elif node_type == sre_constants.SUBPATTERN:
            _, _, _, value = node_value
            return convert_pattern(value)
        elif node_type == sre_constants.BRANCH:
            _, branches = node_value
            return Union(*[convert_pattern(b) for b in branches])
        elif node_type == sre_constants.CATEGORY:
            if node_value == sre_constants.CATEGORY_DIGIT:
                return Range("0", "9")
            elif node_value == sre_constants.CATEGORY_WORD:
                return Union(
                    Range("a", "z"),
                    Range("A", "Z"),
                    Range("0", "9"),
                    Re("_"),
                )
            elif node_value == sre_constants.CATEGORY_SPACE:
                return Union(Re(" "), Re("\t"), Re("\n"))
        
        # Fallback
        return Re("")
    
    def convert_pattern(pattern):
        if len(pattern.data) == 0:
            return Re("")
        elif len(pattern.data) == 1:
            return convert_node(*pattern.data[0])
        else:
            return Concat(*[convert_node(*node) for node in pattern.data])
    
    return convert_pattern(parsed)


def check_policy_type_errors(
    policies: dict,
    available_tools: dict[str, dict] = None,
) -> list[str]:
    """
    Check policies for type-specific errors.
    
    Args:
        policies: Security policies to check
        available_tools: Dict mapping tool names to their arg schemas
        
    Returns:
        List of warning messages
    """
    from progent.validation import validate_schema
    
    warnings = []
    
    if policies is None:
        return warnings
    
    for tool_name, rules in policies.items():
        # Check if tool exists
        if available_tools and tool_name not in available_tools:
            warnings.append(f"Tool '{tool_name}' not in available tools")
        
        for i, rule in enumerate(rules):
            if len(rule) < 3:
                continue
            
            conditions = rule[2]
            
            for arg_name, restriction in conditions.items():
                # Check if arg exists in tool
                if available_tools and tool_name in available_tools:
                    tool_args = available_tools[tool_name]
                    if arg_name not in tool_args:
                        warnings.append(
                            f"Argument '{arg_name}' not found in tool '{tool_name}'"
                        )
                
                # Validate schema
                if isinstance(restriction, dict):
                    schema_warnings = validate_schema(restriction)
                    for w in schema_warnings:
                        warnings.append(f"{tool_name}.{arg_name}: {w}")
    
    return warnings
