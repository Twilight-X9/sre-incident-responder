import os
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
    """Client SDK to interact with the SRE simulation server."""
    
    def __init__(self, base_url: str):
        self.base_url = base_url
        # Give it a healthy timeout since LLMs can take a bit
        self.client = httpx.AsyncClient(base_url=self.base_url, timeout=45.0)

    @classmethod
    async def from_docker_image(cls, image_name: Optional[str] = None):
        # Defaulting to localhost:7860 to match HF Spaces exposed port
        url = os.getenv("ENV_BASE_URL", "http://localhost:7860")
        return cls(base_url=url)

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