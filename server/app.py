import logging
from fastapi import FastAPI, Body
from pydantic import BaseModel
from sre_env.models import SREAction, SREObservation

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="SRE Incident Responder")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "SRE Environment is running."}
# ---------------------------------------------------

class EnvState:
    def __init__(self, task="easy"):
        self.task, self.tick, self.score, self.done = task, 0, 0.01, False
        self.last_output = "System booted. Awaiting command."
        
        if task == "easy":
            self.alerts = ["CRITICAL [frontend]: memory 99%"]
            self.problem_service, self.solution = "frontend", "RESTART_SERVICE"
            self.logs = {"frontend": "OutOfMemoryError", "db": "OK"}
        elif task == "medium":
            self.alerts = ["HIGH [auth]: HTTP 500"]
            self.problem_service, self.solution = "auth", "ROLLBACK_DEPLOYMENT"
            self.logs = {"auth": "SyntaxError in auth.py", "db": "OK"}
        else:
            self.alerts = ["CRITICAL [api]: timeout", "WARNING [db]: pool exhausted"]
            self.problem_service, self.solution = "db", "KILL_DB_QUERY"
            self.logs = {"api": "Timeout", "db": "LOCK WAIT TIMEOUT"}

current_state = EnvState()

class ResetRequest(BaseModel): 
    task: str = "easy"

def _obs() -> SREObservation:
    return SREObservation(
        tick=current_state.tick, 
        active_alerts=current_state.alerts, 
        last_command_output=current_state.last_output, 
        resolved=(len(current_state.alerts) == 0)
    )

@app.post("/reset")
def reset_env(req: ResetRequest = Body(default_factory=ResetRequest)):
    global current_state
    current_state = EnvState(task=req.task)
    return {"observation": _obs().model_dump()}

@app.post("/step")
def step_env(action: SREAction):
    global current_state
    if current_state.done: 
        return {"observation": _obs().model_dump(), "reward": 0.01, "done": True, "info": {}}

    current_state.tick += 1
    reward = 0.01
    
    if action.target_service == current_state.problem_service:
        if action.action_type in ["CHECK_METRICS", "TAIL_LOGS"]:
            current_state.last_output = current_state.logs.get(action.target_service, "No logs.")
            reward = 0.2  
        elif action.action_type == current_state.solution:
            current_state.last_output = f"SUCCESS: {action.action_type} executed."
            current_state.alerts, current_state.done, reward = [], True, 0.8  
        else:
            current_state.last_output = "Failed."
            reward = -0.1 
    else:
        current_state.last_output = "Wasted time on healthy service."
        reward = -0.2

    current_state.score = max(0.01, min(current_state.score + reward, 0.99))
    if current_state.tick >= 6 and not current_state.done:
        current_state.done, current_state.last_output = True, "SLA breached!"

    return {
        "observation": _obs().model_dump(), 
        "reward": reward, 
        "done": current_state.done, 
        "info": {"score": current_state.score}
    }

@app.get("/state")
def get_state(): 
    return {"task": current_state.task, "tick": current_state.tick, "score": current_state.score, "done": current_state.done}
