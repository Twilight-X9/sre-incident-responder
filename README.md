# 🚀 SRE Incident Responder - OpenEnv Hackathon

## 💡 The Problem
In the real world, AI agents need to do more than classify text. They need to navigate complex, stateful environments. When a cloud server crashes, engineers don't blindly restart things—they check metrics, tail logs, form a hypothesis, and *then* execute a fix.

**SRE Incident Responder** simulates a live DevOps production cluster. The AI agent acts as the on-call engineer. It must investigate active alerts, safely query the system state, and take action before the SLA breaches.

## 🛠 Action & Observation Space
- **Observation**: `tick` (int), `active_alerts` (list), `last_command_output` (string), `resolved` (bool).
- **Action**: JSON object containing `action_type` (e.g., `TAIL_LOGS`, `RESTART_SERVICE`, `KILL_DB_QUERY`) and `target_service`.

## 🎯 Reward Shaping (Why this environment is great for RL)
This environment uses highly deliberate reward shaping to train safe agents:
1. **Exploration Reward (+0.2)**: Awarded if the agent queries the logs/metrics of the *correct* failing service.
2. **Resolution Reward (+0.8)**: Awarded for applying the correct fix.
3. **Reckless Penalty (-0.2)**: Strongly penalizes agents that attempt to restart or rollback *healthy* services.

## 🚀 Setup & Testing Locally
1. Install dependencies: `pip install -r requirements.txt`
2. Start the simulation backend: `uvicorn server:app --port 7860`
3. Export your HF API Token: `export HF_TOKEN="your_token_here"`
4. Run the baseline agent evaluator: `python inference.py`