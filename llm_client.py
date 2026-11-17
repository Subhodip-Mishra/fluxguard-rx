"""
FluxGuard RX - LLM Client
Handles real LLM API calls (Groq / OpenAI).
Strictly adheres to:
- No mocks, no stubs, no fake outputs.
- Immediate error propagation on persistent API failure.
- Detailed logging of every call to calls.log (agent name, model, prompt, raw response, latency).
"""

import os
import json
import re
import time
import requests
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

LOG_FILE = "calls.log"

def log_call(agent_name: str, model: str, system_prompt: str, user_prompt: str, raw_response: str, latency: float, error: str = None):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
    entry = (
        f"================================================================================\n"
        f"TIMESTAMP:    {timestamp}\n"
        f"AGENT:        {agent_name}\n"
        f"MODEL:        {model}\n"
        f"LATENCY:      {latency:.3f}s\n"
        f"STATUS:       {'ERROR' if error else 'SUCCESS'}\n"
        f"-------------------------------- SYSTEM PROMPT ---------------------------------\n"
        f"{system_prompt.strip()}\n"
        f"--------------------------------- USER PROMPT ----------------------------------\n"
        f"{user_prompt.strip()}\n"
        f"--------------------------------- RAW RESPONSE ---------------------------------\n"
        f"{(error if error else raw_response).strip()}\n"
        f"================================================================================\n\n"
    )
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(entry)

class LLMClient:
    def __init__(self):
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        
        if self.groq_api_key:
            self.provider = "groq"
            self.api_key = self.groq_api_key
            self.base_url = "https://api.groq.com/openai/v1/chat/completions"
            self.model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        elif self.openai_api_key:
            self.provider = "openai"
            self.api_key = self.openai_api_key
            self.base_url = "https://api.openai.com/v1/chat/completions"
            self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        else:
            raise ValueError("CRITICAL: No API key found. Set GROQ_API_KEY or OPENAI_API_KEY in .env.")

    def chat(self, system_prompt: str, user_prompt: str, agent_name: str = "GenericAgent", temperature: float = 0.0, max_retries: int = 4) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": 600
        }
        
        last_err = None
        for attempt in range(1, max_retries + 1):
            start_time = time.time()
            try:
                response = requests.post(self.base_url, headers=headers, json=data, timeout=35)
                latency = time.time() - start_time
                
                # Proactive rate-limit smoothing
                rem_tokens = response.headers.get("x-ratelimit-remaining-tokens")
                if rem_tokens and rem_tokens.isdigit() and int(rem_tokens) < 150:
                    time.sleep(1.0)

                if response.status_code == 200:
                    res_json = response.json()
                    msg = res_json["choices"][0]["message"]
                    raw_content = msg.get("content", "").strip()
                    if not raw_content and "reasoning" in msg:
                        raw_content = msg["reasoning"].strip()
                    log_call(agent_name, self.model, system_prompt, user_prompt, raw_content, latency)
                    return raw_content
                
                # Handle 429 Rate Limit
                elif response.status_code == 429:
                    error_text = response.text
                    match = re.search(r"try again in ([\d\.]+)s", error_text)
                    sleep_time = (float(match.group(1)) + 1.0) if match else (2.0 * attempt)
                    log_call(agent_name, self.model, system_prompt, user_prompt, "", latency, error=f"Rate Limit: {error_text}. Backing off {sleep_time:.2f}s (attempt {attempt}/{max_retries})")
                    time.sleep(sleep_time)
                    last_err = RuntimeError(f"API Error HTTP 429: {error_text}")
                else:
                    err_msg = f"API Error HTTP {response.status_code}: {response.text}"
                    log_call(agent_name, self.model, system_prompt, user_prompt, "", latency, error=err_msg)
                    raise RuntimeError(err_msg)
                    
            except Exception as e:
                latency = time.time() - start_time
                if not isinstance(e, RuntimeError) or "429" not in str(e):
                    log_call(agent_name, self.model, system_prompt, user_prompt, "", latency, error=str(e))
                # Stop immediately on permanent client errors (400, 401, 403, 404)
                if isinstance(e, RuntimeError) and any(code in str(e) for code in ["HTTP 400", "HTTP 401", "HTTP 403", "HTTP 404"]):
                    raise
                last_err = e
                time.sleep(1.5 * attempt)
        
        raise RuntimeError(f"Call failed after {max_retries} attempts: {last_err}")

    def chat_json(self, system_prompt: str, user_prompt: str, agent_name: str = "GenericAgent") -> dict:
        raw = self.chat(system_prompt, user_prompt, agent_name=agent_name, temperature=0.0)
        
        # 1. Clean markdown fences
        block_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', raw, re.DOTALL)
        if block_match:
            try:
                return json.loads(block_match.group(1))
            except json.JSONDecodeError:
                pass

        # 2. Try outermost curly braces
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        # 3. Handle unclosed trailing brace
        if "{" in raw:
            sub = raw[raw.index("{"):].strip()
            if sub.count('"') % 2 != 0:
                sub += '"'
            if not sub.endswith("}"):
                sub += "}"
            try:
                return json.loads(sub)
            except json.JSONDecodeError:
                pass

        # 4. Regex extraction fallback
        status_match = re.search(r'"status"\s*:\s*"([^"]+)"', raw, re.IGNORECASE)
        reason_match = re.search(r'"reason"\s*:\s*"([^"]+)', raw, re.IGNORECASE)
        if status_match:
            return {
                "status": status_match.group(1).strip(),
                "reason": reason_match.group(1).rstrip('",}').strip() if reason_match else ""
            }
                
        raise ValueError(f"Failed to parse JSON response from LLM:\n{raw}")
