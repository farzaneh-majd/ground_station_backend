import asyncio
from collections import defaultdict

class EventBus:
    def __init__(self): self.listeners=defaultdict(set)
    async def publish(self,kind,item):
        for queue in tuple(self.listeners[kind]):
            try: queue.put_nowait(item)
            except asyncio.QueueFull:
                try: queue.get_nowait();queue.put_nowait(item)
                except asyncio.QueueEmpty: pass
    async def stream(self,kind):
        queue=asyncio.Queue(maxsize=200)
        self.listeners[kind].add(queue)
        try:
            while True: yield await queue.get()
        finally: self.listeners[kind].discard(queue)
# In-process event bus: for multi-worker deployments replace with Redis/NATS.
bus=EventBus()
