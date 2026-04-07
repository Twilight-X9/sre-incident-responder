import logging
from fastapi import FastAPI, Body
from pydantic import BaseModel
from sre_env.models import SREAction, SREObservation

# Set up basic logging so we can see what's happening locally
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sre_env")

app = FastAPI(title="SRE Incident Responder")

class EnvState:
    def __init__(self, task="easy"):
        self.task = task
        self.tick = 0
        self.score = 0.0
        self.done = False
        self.last_output = "System booted. Awaiting command."
        
        # Scenario definitions
        if task == "easy":
            self.alerts = ["CRITICAL [frontend_service]: memory usage at 99%"]
            self.problem_service = "frontend_service"
            self.solution = "RESTART_SERVICE"
            self.logs = {
                "frontend_service": "java.lang.OutOfMemoryError: Java heap space", 
                "db": "DB Status: OK"
            }
        elif task == "medium":
            self.alerts = ["HIGH[auth_service]: HTTP 500 error spike detected"]
            self.problem_service = "auth_service"
            self.solution = "ROLLBACK_DEPLOYMENT"
            self.logs = {
                "auth_service": "Traceback: SyntaxError in auth_controller.py v2.1 (recent deploy)", 
                "db": "DB Status: OK"
            }
        else: # hard task
            self.alerts =["CRITICAL [api_gateway]: timeout", "WARNING [db]: connection pool exhausted"]
            self.problem_service = "db"
            self.solution = "KILL_DB_QUERY"
            self.logs = {
                "api_gateway": "Error: Timed out waiting for DB connection pool", 
                "db": "LOCK WAIT TIMEOUT EXCEEDED; Query: SELECT * FROM huge_table_v2"
            }

# Global state isn't perfectly thread-safe, but it's standard for OpenEnv single-agent testing
current_state = EnvState()

class ResetRequest(BaseModel):
    task: str = "easy"

def _build_obs() -> SREObservation:
    return SREObservation(
        tick=current_state.tick, 
        active_alerts=current_state.alerts, 
        last_command_output=current_state.last_output, 
        resolved=(len(current_state.alerts) == 0)
    )

@app.post("/reset")
def reset_env(req: ResetRequest = Body(default_factory=ResetRequest)):
    global current_state
    logger.info(f"Resetting environment with task: {req.task}")
    current_state = EnvState(task=req.task)
    return {"observation": _build_obs().model_dump()}

@app.post("/step")
def step_env(action: SREAction):
    global current_state
    
    if current_state.done:
        return {"observation": _build_obs().model_dump(), "reward": 0.0, "done": True, "info": {"error": "Episode already finished"}}

    current_state.tick += 1
    reward = 0.0
    
    # Evaluate the agent's action
    if action.target_service == current_state.problem_service:
        if action.action_type in["CHECK_METRICS", "TAIL_LOGS"]:
            # Give a small partial reward for investigating the correct service
            current_state.last_output = current_state.logs.get(action.target_service, "No logs found.")
            reward = 0.2  
        elif action.action_type == current_state.solution:
            # Jackpot! They fixed it.
            current_state.last_output = f"SUCCESS: {action.action_type} executed. Incident resolved."
            current_state.alerts =[]
            current_state.done = True
            reward = 0.8  
        else:
            # Right service, wrong fix
            current_state.last_output = "Command executed, but the service is still failing."
            reward = -0.1 
    else:
        # Penalize them for touching healthy services. We don't want reckless agents!
        current_state.last_output = f"Executed on {action.target_service}. Service was healthy. You wasted time."
        reward = -0.2

    # Update cumulative score and clamp between 0 and 1 as per spec rules
    current_state.score += reward
    current_state.score = max(0.0, min(current_state.score, 1.0))

    # Auto-fail if they take too many turns (simulate SLA breach)
    if current_state.tick >= 6 and not current_state.done:
        current_state.done = True
        current_state.last_output = "SLA breached! Incident escalated to a human engineer."

    return {
        "observation": _build_obs().model_dump(), 
        "reward": reward, 
        "done": current_state.done, 
        "info": {"cumulative_score": current_state.score}
    }

@app.get("/state")
def get_state():
    return {
        "task": current_state.task, 
        "tick": current_state.tick, 
        "score": current_state.score, 
        "done": current_state.done
    }
@app.get("/")
def health_check():
    return {"status": "SRE Environment is Live"}