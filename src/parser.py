from typing import Iterator, Optional
from lark import Lark, Tree, v_args
from lark.visitors import Interpreter
from sim_objects import SimObject
from tqdm import tqdm
import os

@v_args(inline=True)
class FormulaEvaluator(Interpreter):
    """
    Implements the logic to check if a given assignment satisfies a formula for a given world.
    """

    def __init__(self, world: list[SimObject], assignments: Optional[dict[str, list[SimObject | bool | None]]] = None):
        """
        Initializes the transformer with a world and optional assignments.
        :param world: The list of SimObjects to consider for this formula.
        :param assignments: A dictionary mapping variable names to SimObject IDs. 
            If None, an empty dictionary is used. CAUTION: If a variable is provided in the assignment,
            any existential formula binding this variable will ONLY be evaluated against the provided object
            and not against all objects in the world!
        """
        self.world = world
        self.assignments: dict[str, list[SimObject | bool | None]] = assignments if assignments is not None else {}

    def _get_obj(self, var_name):
        if var_name not in self.assignments:
            raise NameError(f"Variable '{var_name}' is not bound.")
        assigned_obj = self.assignments[var_name]
        if assigned_obj[1]:
            assert isinstance(assigned_obj[0], SimObject), f"Expected a SimObject, got {type(assigned_obj[0])} for variable '{var_name}'"
            return assigned_obj[0]
        raise NameError(f"Variable '{var_name}' is not bound.")
        

    # --- Literal and Variable Handling ---
    def ESCAPED_STRING(self, s): return s.value[1:-1]  # Remove quotes
    def SIGNED_NUMBER(self, n): return float(n.value)
    def CNAME(self, n): return str(n.value)
    def INT(self, n): return int(n.value)
    def parse_token(self, t):
        match t.type:
            case "ESCAPED_STRING": return self.ESCAPED_STRING(t)
            case "SIGNED_NUMBER": return self.SIGNED_NUMBER(t) 
            case "CNAME": return self.CNAME(t)
            case "INT": return self.INT(t)
        raise ValueError(f"Unexpected token type: {t.type}")

    # --- Logical Connectives ---
    def equivalence_formula(self, *forms): 
        first_value = self.visit(forms[0])
        return all(self.visit(x) == first_value for x in forms[1:])
    def implication_formula(self, *forms):
        forms = forms[::-1]
        val = self.visit(forms[0])
        for form in forms[1:]:
            curr = self.visit(form)
            if curr > val:
                return False
            val = curr
        return True
    def or_formula(self, *forms): return any(self.visit(form) for form in forms)
    def and_formula(self, *forms): return all(self.visit(form) for form in forms)
    def negation_formula(self, inner): return not self.visit(inner)
    
    # --- Quantifiers ---
    def exists_formula(self, var_name, sub_formula):
        # If the variable is already bound, we only check the sub-formula
        if var_name in self.assignments: return self.visit(sub_formula)
        var_name = str(var_name)  # Ensure var_name is a string
        # We keep track of the previous state of assignments for resetting the scope later
        old_value = self.assignments.get(var_name)
        try:
            self.assignments[var_name] = [None, True]  # Mark as bound but not assigned
            for obj in self.world:
                self.assignments[var_name][0] = obj
                if self.visit(sub_formula):
                    return True
            return False
        finally:
            self.assignments[var_name][1] = False  # Mark as unbound
            if old_value:
                self.assignments[var_name] = old_value
    
    def forall_formula(self, var_name, sub_formula):
        # We keep track of the previous state of assignments for resetting the scope later
        old_value = self.assignments.get(var_name)
        var_name = str(var_name)  # Ensure var_name is a string
        try:
            self.assignments[var_name] = [None, True]  # Mark as bound but not assigned
            for obj in self.world:
                self.assignments[var_name][0] = obj
                if not self.visit(sub_formula):
                    return False
            return True
        finally:
            self.assignments[var_name][1] = False  # Mark as unbound
            if old_value:
                self.assignments[var_name] = old_value
                
    def connects_formula(self, from_var, to_var, sub_formula):
        from_var = str(from_var)
        to_var = str(to_var)
        if not self._get_obj(from_var):
            raise NameError(f"Variable '{from_var}' is not bound.")
        connections = self.assignments[from_var][0].connections #type: ignore
        old_var = self.assignments.get(to_var)
        try:
            self.assignments[to_var] = [None, True]  
            for obj in connections:
                self.assignments[to_var][0] = next(o for o in self.world if o.obj_id == obj)
                if self.visit(sub_formula):
                    return True
            return False
        finally:
            self.assignments[to_var][1] = False
            if old_var:
                self.assignments[to_var] = old_var

    # --- Predicates ---
    def body_predicate(self, var): return self._get_obj(var).get_object_class() == "Body"
    def force_element_predicate(self, var): return self._get_obj(var).get_object_class() == "ForceElement"
    def constraint_predicate(self, var): return self._get_obj(var).get_object_class() == "Constraint"
    def connection_predicate(self, var): return self._get_obj(var).get_object_class() == "Connection"
    def joint_predicate(self, var): return self._get_obj(var).get_object_class() == "Joint"
    def type_predicate(self, var, type_name): return self._get_obj(var).object_type == self.parse_token(type_name)
    def equality_predicate(self, var1, var2): return self._get_obj(var1) == self._get_obj(var2)
    
    def connecting_predicate(self, var1, var2):
        obj1 = self._get_obj(var1)
        obj2 = self._get_obj(var2)
        return (obj1.obj_id in obj2.connections) or (obj2.obj_id in obj1.connections)

    def is_predicate(self, var, param, val):
        obj = self._get_obj(var)
        actual = obj.get_param(self.parse_token(param)) # type: ignore
        if actual is None:
            return False
        val = self.parse_token(val)
        if isinstance(actual, (int, float)):
            return actual == val
        elif isinstance(actual, str) and isinstance(val, str):
            return actual.lower() == val.lower()
        return False

    def lt_predicate(self, var, param, val):
        obj = self._get_obj(var)
        actual = obj.get_param(self.parse_token(param)) # type: ignore
        if actual is None:
            return False
        val = self.parse_token(val)
        if isinstance(actual, (int, float)) and isinstance(val, (int, float)):
            return actual < val
        return False

    def gt_predicate(self, var, param, val):
        obj = self._get_obj(var)
        actual = obj.get_param(self.parse_token(param)) # type: ignore
        if actual is None:
            return False
        val = self.parse_token(val)
        if isinstance(actual, (int, float)) and isinstance(val, (int, float)):
            return actual > val 
        return False
        
class Solver:
    """
    A simple solver that evaluates a formula against a world and optional assignments.
    """

    def __init__(self, world: list[SimObject], assignment_factory: Optional[Iterator[dict[str, SimObject]]] = None):
        self.world = world
        self.assignment_generator = assignment_factory 
        # Not implemented yet, but could be used to generate assignments using a heuristic
        self.parser = Lark.open("grammar.lark", parser="earley", rel_to=os.path.realpath(__file__))

    def solve(self, formula: str) -> set[SimObject]:
        tree = self.parser.parse(formula)
        
        primary_var = str(tree.children[0])
        entry_formula = tree.children[1]
        solutions = set()
        
        evaluator = FormulaEvaluator(self.world)
        
        for obj in tqdm(self.world, desc="Solving formula", unit="candidates"):
            assignments = {primary_var: [obj, True]}
            evaluator.assignments = assignments
            if evaluator.visit(entry_formula):
                solutions.add(str(list(map(lambda x: (x, evaluator.assignments[x][0].obj_id), evaluator.assignments))))
        return solutions
        