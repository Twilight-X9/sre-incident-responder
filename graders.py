# sre_env/graders.py

def grade_easy(env_state) -> float:
    # Logic to evaluate if the easy task is completed
    if env_state.task == "easy" and env_state.done:
        return 1.0
    return 0.0

def grade_medium(env_state) -> float:
    # Logic to evaluate if the medium task is completed
    if env_state.task == "medium" and env_state.done:
        return 1.0
    return 0.0

def grade_hard(env_state) -> float:
    # Logic to evaluate if the hard task is completed
    if env_state.task == "hard" and env_state.done:
        return 1.0
    return 0.0