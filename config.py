# Configuration for SRE Incident Responder
import os

# Server Settings
SERVER_HOST = "0.0.0.0"
SERVER_PORT = 7860

# Environment Settings
SLA_TICK_LIMIT = 6
DEFAULT_SCORE_MIN = 0.01
DEFAULT_SCORE_MAX = 0.99

# Inference Settings
MODEL_NAME = os.getenv("MODEL_NAME", "Qwen/Qwen2.5-72B-Instruct")
MAX_STEPS = 6
TEMPERATURE = 0.1
MAX_TOKENS = 150
