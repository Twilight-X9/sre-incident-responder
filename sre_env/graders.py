from typing import Any

def _evaluate_state(*args: Any, **kwargs: Any) -> float:
    for arg in args:
        if hasattr(arg, 'resolved'): 
            return 0.99 if arg.resolved else 0.01
        if isinstance(arg, dict) and 'resolved' in arg: 
            return 0.99 if arg['resolved'] else 0.01
            
    for val in kwargs.values():
        if hasattr(val, 'resolved'): 
            return 0.99 if val.resolved else 0.01
        if isinstance(val, dict) and 'resolved' in val: 
            return 0.99 if val['resolved'] else 0.01
            
    return 0.01

def grade_easy(*args: Any, **kwargs: Any) -> float: 
    return _evaluate_state(*args, **kwargs)

def grade_medium(*args: Any, **kwargs: Any) -> float: 
    return _evaluate_state(*args, **kwargs)

def grade_hard(*args: Any, **kwargs: Any) -> float: 
    return _evaluate_state(*args, **kwargs)

def grade(self, *args, **kwargs):
    raw_score = calculate_score() 
    
    final_score = max(0.01, min(0.99, raw_score))
    return final_score

