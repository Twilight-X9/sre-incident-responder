import os

# 1. Create the missing sre_env directory
os.makedirs("sre_env", exist_ok=True)

# 2. Create __init__.py
with open("sre_env/__init__.py", "w", encoding="utf-8") as f:
    f.write("from .models import SREAction, SREObservation\nfrom .environment import SREEnv\n__all__ = ['SREAction', 'SREObservation', 'SREEnv']\n")

# 3. Create models.py
with open("sre_env/models.py", "w", encoding="utf-8") as f:
    f.write("""from pydantic import BaseModel
from typing import Literal

class SREAction(BaseModel):
    action_type: Literal["CHECK_METRICS", "TAIL_LOGS", "RESTART_SERVICE", "ROLLBACK_DEPLOYMENT", "KILL_DB_QUERY"]
    target_service: str

class SREObservation(BaseModel):
    tick: int
    active_alerts: list[str]
    last_command_output: str
    resolved: bool
""")

# 4. Create environment.py
with open("sre_env/environment.py", "w", encoding="utf-8") as f:
    f.write("""import os
import httpx
from typing import Optional
from pydantic import BaseModel
from .models import SREAction, SREObservation

class StepResult(BaseModel):
    observation: SREObservation
    reward: float
    done: bool
    info: dict

class ResetResult(BaseModel):
    observation: SREObservation

class SREEnv:
    def __init__(self, base_url: str):
        self.client = httpx.AsyncClient(base_url=base_url, timeout=45.0)

    @classmethod
    async def from_docker_image(cls, image_name: Optional[str] = None):
        return cls(base_url=os.getenv("ENV_BASE_URL", "http://localhost:7860"))

    async def reset(self, task: str = "easy") -> ResetResult:
        resp = await self.client.post("/reset", json={"task": task})
        resp.raise_for_status()
        return ResetResult(observation=SREObservation(**resp.json()["observation"]))

    async def step(self, action: SREAction) -> StepResult:
        resp = await self.client.post("/step", json=action.model_dump())
        resp.raise_for_status()
        data = resp.json()
        return StepResult(
            observation=SREObservation(**data["observation"]),
            reward=data["reward"],
            done=data["done"],
            info=data["info"]
        )

    async def close(self):
        await self.client.aclose()
""")

print("✅ SUCCESS! The 'sre_env' module has been created. You can now start the server!")