import asyncio
import os
import json
import textwrap
from typing import List, Optional

from openai import OpenAI

from sre_env.models import SREAction
from sre_env.environment import SREEnv

# Pull from environment per spec requirements
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
TASK_NAME = os.getenv("SRE_TASK", "hard") 
BENCHMARK = "sre_incident_responder"

MAX_STEPS = 6

SYSTEM_PROMPT = textwrap.dedent("""
    You are an expert SRE. 
    STRATEGY:
    1. Look at ALL alerts. If one service is a gateway and another is a DB, the DB is usually the root cause.
    2. If 'last_command_output' says a service is healthy or an action wasted time, DO NOT repeat that action.
    3. You must investigate the 'db' service if alerts mention connection pools or locks.
    
    Allowed action_types: CHECK_METRICS, TAIL_LOGS, RESTART_SERVICE, ROLLBACK_DEPLOYMENT, KILL_DB_QUERY
    
    Respond ONLY with JSON: {"action_type": "TAIL_LOGS", "target_service": "db"}
""").strip()
# ---- MANDATORY STDOUT FORMATTING LOGIC ----
def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)

def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    err_str = error if error else "null"
    print(f"[STEP] step={step} action={action} reward={reward:.2f} done={str(done).lower()} error={err_str}", flush=True)

def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    r_str = ",".join(f"{r:.2f}" for r in rewards)
    print(f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={r_str}", flush=True)
# -------------------------------------------

def decide_action(client: OpenAI, obs) -> SREAction:
    user_prompt = f"Tick: {obs.tick}\nAlerts: {obs.active_alerts}\nLast Output: {obs.last_command_output}\nWhat is your next action?"
    
    try:
        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT}, 
                {"role": "user", "content": user_prompt}
            ],
            temperature=0.1, # Keep it low for deterministic JSON
            max_tokens=150,
        )
        
        raw_text = completion.choices[0].message.content.strip()
        
        # Hacky way to strip markdown if the LLM decides to wrap it in ```json ... ```
        clean_text = raw_text.replace("```json", "").replace("```", "").strip()
        parsed = json.loads(clean_text)
        
        return SREAction(
            action_type=parsed.get("action_type", "CHECK_METRICS"), 
            target_service=parsed.get("target_service", "unknown")
        )
        
    except Exception as e:
        # Fallback so the inference loop doesn't crash on a bad LLM response
        return SREAction(action_type="CHECK_METRICS", target_service="fallback_error")

async def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = await SREEnv.from_docker_image()
    
    rewards: List[float] =[]
    steps_taken = 0
    
    log_start(task=TASK_NAME, env=BENCHMARK, model=MODEL_NAME)
    
    try:
        result = await env.reset(task=TASK_NAME)
        obs = result.observation
        
        for step in range(1, MAX_STEPS + 1):
            if obs.resolved:
                break
                
            action = decide_action(client, obs)
            res = await env.step(action)
            
            obs = res.observation
            reward = res.reward or 0.0
            done = res.done
            
            rewards.append(reward)
            steps_taken = step
            
            action_str = f"{action.action_type}({action.target_service})"
            log_step(step, action_str, reward, done, None)
            
            if done:
                break
                
        # Calculate final normalized score
        total_score = sum(rewards)
        final_score = min(max(total_score, 0.0), 1.0) # Ensure it stays 0.0 to 1.0
        is_success = final_score >= 0.8 # Consider it a win if they scored highly
        
    finally:
        await env.close()
        log_end(is_success, steps_taken, final_score, rewards)

if __name__ == "__main__":
    asyncio.run(main())