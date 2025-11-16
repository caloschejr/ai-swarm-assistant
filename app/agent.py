"""
# app/agent.py
# Uses app.secrets.get("OPENAI_API_KEY") for runtime key and supports NO_KEY_MODE demo fallback.
"""
import asyncio
import os
from typing import Dict, Any

from .secrets import get as get_secret

# Very small LLM client abstraction supporting real OpenAI or demo fallback
class LLMClient:
    def __init__(self, model_name: str = "gpt-placeholder"):
        self.model_name = model_name
        self.openai_key = get_secret("OPENAI_API_KEY")
        self.no_key_mode = os.getenv("NO_KEY_MODE", "0") == "1"

        # If OPENAI_API_KEY present and not in no-key mode, prepare client
        if self.openai_key and not self.no_key_mode:
            try:
                import openai
                openai.api_key = self.openai_key
                self._openai = openai
            except Exception:
                self._openai = None
        else:
            self._openai = None

    async def generate(self, prompt: str, **kwargs) -> str:
        # If OpenAI client is available, call it synchronously in a thread pool
        if self._openai:
            try:
                def call_openai():
                    # Use ChatCompletion if available
                    try:
                        resp = self._openai.ChatCompletion.create(
                            model=kwargs.get("model", "gpt-4o-mini"),
                            messages=[{"role":"user","content":prompt}],
                            max_tokens=kwargs.get("max_tokens", 150)
                        )
                        # Newer SDKs use different response shapes; adapt safely
                        if hasattr(resp, 'choices') and resp.choices:
                            choice = resp.choices[0]
                            # ChatCompletion returns message
                            if hasattr(choice, 'message'):
                                return choice.message.get('content') if isinstance(choice.message, dict) else choice.message.content
                            # Legacy text
                            return getattr(choice, 'text', str(choice))
                        return str(resp)
                    except Exception:
                        # Try the responses API shape
                        if hasattr(self._openai, 'Responses'):
                            res = self._openai.Responses.create(model=kwargs.get('model', 'gpt-4o-mini'), input=prompt)
                            # Try common fields
                            if hasattr(res, 'output'):
                                # output is a list of items
                                try:
                                    return res.output[0].content[0].text
                                except Exception:
                                    return str(res)
                        raise

                loop = asyncio.get_event_loop()
                resp_text = await loop.run_in_executor(None, call_openai)
                return resp_text
            except Exception:
                # Fall through to demo fallback
                pass

        # NO_KEY / Demo fallback — deterministic safe reply
        if self.no_key_mode or not self._openai:
            snippet = prompt.strip().replace("\n", " ")[:300]
            return f"[demo-mode] Echo: {snippet}"

        # Ultimate fallback
        return f"[{self.model_name}] Echo: {prompt[:200]}"


# Agent class uses updated LLMClient
class Agent:
    def __init__(self, agent_id: str, spec: Dict[str, Any]):
        self.id = agent_id
        self.spec = spec
        self.llm = LLMClient(model_name=spec.get("base_model", "gpt-placeholder"))
        self.memory = []

    async def respond(self, prompt: str) -> str:
        role = self.spec.get("role", "assistant")
        tpl = f"Role: {role}\nContext: {self.spec.get('description','')}\nUser: {prompt}\nAgent:"
        resp = await self.llm.generate(tpl)
        self.memory.append({"prompt": prompt, "response": resp})
        return resp


# Simple helper for synchronous callsites
def respond_sync(agent: Agent, prompt: str) -> str:
    return asyncio.get_event_loop().run_until_complete(agent.respond(prompt))
