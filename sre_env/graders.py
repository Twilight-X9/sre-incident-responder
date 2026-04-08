from typing import Any

def _evaluate_state(*args: Any, **kwargs: Any) -> float:
    for arg in args:
        if hasattr(arg, 'resolved'): 
            return 1.0 if arg.resolved else 0.0
        if isinstance(arg, dict) and 'resolved' in arg: 
            return 1.0 if arg['resolved'] else 0.0
            
    for val in kwargs.values():
        if hasattr(val, 'resolved'): 
            return 1.0 if val.resolved else 0.0
        if isinstance(val, dict) and 'resolved' in val: 
            return 1.0 if val['resolved'] else 0.0
            
    return 0.0

def grade_easy(*args: Any, **kwargs: Any) -> float: 
    return _evaluate_state(*args, **kwargs)

def grade_medium(*args: Any, **kwargs: Any) -> float: 
    return _evaluate_state(*args, **kwargs)

def grade_hard(*args: Any, **kwargs: Any) -> float: 
    return _evaluate_state(*args, **kwargs)
