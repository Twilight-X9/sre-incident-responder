from pydantic import BaseModel
from typing import Literal

# Define the exact actions our SRE agent is allowed to take in the cluster.
class SREAction(BaseModel):
    action_type: Literal[
        "CHECK_METRICS", 
        "TAIL_LOGS", 
        "RESTART_SERVICE", 
        "ROLLBACK_DEPLOYMENT", 
        "KILL_DB_QUERY"
    ]
    target_service: str

class SREObservation(BaseModel):
    tick: int
    active_alerts: list[str]
    last_command_output: str
    resolved: bool