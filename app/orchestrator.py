import os
import asyncio
from typing import List, Any

# Allow disabling Ray for single-container/cloud deployments via env var
DISABLE_RAY = os.getenv("DISABLE_RAY", "0") == "1"

RAY_AVAILABLE = False
if not DISABLE_RAY:
    try:
        import ray
        if not ray.is_initialized():
            ray.init(ignore_reinit_error=True)
        RAY_AVAILABLE = True
    except Exception:
        # Ray not available or failed to initialize; fall back to in-process mode
        RAY_AVAILABLE = False

if RAY_AVAILABLE:
    @ray.remote
    class AgentActor:
        def __init__(self, agent_serialized):
            # agent_serialized is a picklable object with minimal spec
            from .agent import Agent
            self.agent = Agent(agent_serialized["id"], agent_serialized["spec"])

        async def respond(self, prompt: str):
            return await self.agent.respond(prompt)

class SwarmOrchestrator:
    async def run_swarm(self, agents: List[Any], prompt: str, max_responses: int = 5):
        """
        Run a swarm of agents. If Ray is available and enabled, use Ray actors.
        Otherwise run agent.respond() concurrently in-process (single-container mode).
        """
        if not RAY_AVAILABLE:
            # In-process concurrent execution (works on single container platforms)
            coros = [a.respond(prompt) for a in agents[:max_responses]]
            results = await asyncio.gather(*coros)
            from collections import Counter
            counter = Counter(results)
            top = counter.most_common(1)[0][0] if counter else ""
            return {"responses": results, "consensus": top}

        # Ray-based path (existing behavior)
        actor_handles = []
        for a in agents[:max_responses]:
            serialized = {"id": a.id, "spec": a.spec}
            actor_handles.append(AgentActor.remote(serialized))

        futures = [actor.respond.remote(prompt) for actor in actor_handles]
        loop = asyncio.get_event_loop()
        results = await loop.run_in_executor(None, ray.get, futures)

        from collections import Counter
        counter = Counter(results)
        top = counter.most_common(1)[0][0] if counter else ""
        return {"responses": results, "consensus": top}