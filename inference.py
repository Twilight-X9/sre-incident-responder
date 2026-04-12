import asyncio
import os
import json
import textwrap
import logging
from typing import List, Optional
from openai import OpenAI
from sre_env.models import SREAction
from sre_env.environment import SREEnv
import config

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = config.MODEL_NAME
BENCHMARK = "sre_incident-responder"
MAX_STEPS = config.MAX_STEPS

SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert Site Reliability Engineer (SRE). Your goal is to diagnose and resolve system incidents in the minimum number of steps.

    DIAGNOSTIC WORKFLOW:
    1. ANALYZE: Look at the active alerts. Identify which service is reporting errors.
    2. EVALUATE: Read the 'last_command_output'. Did the previous action provide a clue or a failure?
    3. HYPOTHESIZE: If the frontend is slow but the DB has locks, the DB is likely the root cause.
    4. ACT: Choose the most logical next step. Use CHECK_METRICS or TAIL_LOGS to confirm a hypothesis, and use fix actions (RESTART_SERVICE, ROLLBACK_DEPLOYMENT, KILL_DB_QUERY) only when you are certain.

    Allowed action_types: CHECK_METRICS, TAIL_LOGS, RESTART_SERVICE, ROLLBACK_DEPLOYMENT, KILL_DB_QUERY

    RESPONSE FORMAT:
    You must respond ONLY with a JSON object containing 'reasoning' (your step-by-step thought process) and the action details.
    Example:
    {
        "reasoning": "The frontend is reporting 99% memory. I will first check the logs to see if it is a memory leak or a specific crash.",
        "action_type": "TAIL_LOGS",
        "target_service": "frontend"
    }
    """).strip()


def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    err_str = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={err_str}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    r_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={r_str}", flush=True)

def decide_action(client: OpenAI, obs) -> SREAction:
    user_prompt = f"Tick: {obs.tick}\nAlerts: {obs.active_alerts}\nLast Output: {obs.last_command_output}\nWhat is your next action?"
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt}
            ],
            temperature=config.TEMPERATURE,
            max_tokens=config.MAX_TOKENS,
        )
        raw_text = completion.choices[0].message.content.strip()
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_text)
        return SREAction(
            action_type=parsed.get("action_type", "CHECK_METRICS"),
            target_service=parsed.get("target_service", "unknown")
        )
    except Exception as e:
        return SREAction(action_type="CHECK_METRICS", target_service="fallback_error")

async def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = await SREEnv.from_docker_image()
    
    tasks_to_run = ["easy", "medium", "hard"]
    
    for task in tasks_to_run:
        log_start(task=task, env=BENCHMARK, model=MODEL_NAME)
        reset_res = await env.reset(task=task)
        obs = reset_res.observation
        
        rewards = []
        steps = 0
        done = False
        success = False
        final_score = 0.01
        
        while not done and steps < MAX_STEPS:
            steps += 1
            action = decide_action(client, obs)
            step_res = await env.step(action)
            obs = step_res.observation
            reward = step_res.reward
            done = step_res.done
            
            rewards.append(reward)
            action_str = f"{action.action_type}({action.target_service})"
            log_step(step=steps, action=action_str, reward=reward, done=done, error=None)
            
            final_score = step_res.info.get("score", 0.01)
            if done and final_score > 0.5:
                success = True
                
        log_end(success=success, steps=steps, score=final_score, rewards=rewards)

    await env.close()

if __name__ == "__main__":
    asyncio.run(main())
