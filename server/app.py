import logging
import uvicorn
from fastapi import FastAPI, Body
from pydantic import BaseModel
from sre_env.models import SREAction, SREObservation
from config import SERVER_HOST, SERVER_PORT, SLA_TICK_LIMIT, DEFAULT_SCORE_MIN, DEFAULT_SCORE_MAX

logging.basicConfig(level=logging.INFO)
app = FastAPI(title="SRE Incident Responder")

@app.get("/")
def health_check():
    return {"status": "ok", "message": "SRE Environment is running."}
# ---------------------------------------------------

class EnvState:
    def __init__(self, task="easy"):
        self.task, self.tick, self.score, self.done = task, 0, DEFAULT_SCORE_MIN, False
        self.last_output = "System booted. Awaiting command."
        
        if task == "easy":
            self.alerts = ["CRITICAL [frontend]: memory 99%"]
            self.problem_service, self.solution = "frontend", "RESTART_SERVICE"
            self.logs = {
                "frontend": "2026-04-12 10:00:01 ERROR [main] - java.lang.OutOfMemoryError: Java heap space\n  at com.app.Frontend.process(Frontend.java:42)",
                "db": "2026-04-12 10:00:01 INFO [main] - Database health check: OK"
            }
        elif task == "medium":
            self.alerts = ["HIGH [auth]: HTTP 500 Internal Server Error"]
            self.problem_service, self.solution = "auth", "ROLLBACK_DEPLOYMENT"
            self.logs = {
                "auth": "2026-04-12 10:05:22 CRITICAL [auth.py] - SyntaxError: invalid syntax at line 114 in auth_middleware.py",
                "db": "2026-04-12 10:05:22 INFO [main] - Database health check: OK"
            }
        else:
            # Hard mode: Cascading failure. API is failing because DB is locked.
            self.alerts = ["CRITICAL [api]: Gateway Timeout", "WARNING [db]: connection_pool_exhausted"]
            self.problem_service, self.solution = "db", "KILL_DB_QUERY"
            self.logs = {
                "api": "2026-04-12 10:10:05 ERROR [api] - Upstream timeout waiting for database response (5000ms)\n  at api.request_handler.py:88",
                "db": "2026-04-12 10:10:01 WARN [db_engine] - Long running query detected: SELECT * FROM large_table WHERE status='pending' (PID: 8821) LOCK WAIT TIMEOUT"
            }

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

    current_state.score = max(DEFAULT_SCORE_MIN, min(current_state.score + reward, DEFAULT_SCORE_MAX))
    if current_state.tick >= SLA_TICK_LIMIT and not current_state.done:
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

def main():
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)

if __name__ == "__main__":
    main()
