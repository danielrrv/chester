
from __future__ import annotations
import asyncio
from concurrent.futures import ThreadPoolExecutor
from contextlib import AsyncExitStack, asynccontextmanager
import queue
import threading
import time
from typing import Any, AsyncGenerator, Callable, Generator, List, Self, Set


class AsyncGeneratorTarget:
    def __init__(self, func,  *args, **kwargs):
        self.func = func
        self.args = args
        self.kwargs = kwargs

   
        
class AsyncExecutor:
    def __init__(self):
        try:
            self.loop = asyncio.get_running_loop()
        except RuntimeError:
            self.loop = asyncio.get_event_loop()
        self.background_tasks = set()
        self.queue = asyncio.Queue()
        
    async def _run_async_func(self, t: AsyncGeneratorTarget):
        try:
            async for message in t.func(*t.args, **t.kwargs):
                await self.queue.put(message)  # Use await to respect backpressure
        except Exception as e:
            # Prevent silent failures in background tasks
            print(f"Error in background generator: {e}")
        finally:
            pass
   
    async def join(self):
        if self.background_tasks:
            # Wait for all producers to finish generating items
            await asyncio.gather(*self.background_tasks, return_exceptions=True)
        # Signal to the consumer queue that no more data is coming
        await self.queue.put(None)


    def run_async(self, t: AsyncGeneratorTarget):
        task = self.loop.create_task(self._run_async_func(t))
        self.background_tasks.add(task)
        task.add_done_callback(self.background_tasks.discard)        
    
    
    async def read_from_queue(self) -> AsyncGenerator[Any, None]:
        while True:
            # Fixed: Standard await blocks gracefully until data is available
            item = await self.queue.get()
            if item is None:
                self.queue.task_done()
                break
            yield item
            self.queue.task_done()

    @classmethod
    @asynccontextmanager
    async def run(cls, targets: List[AsyncGeneratorTarget]) -> AsyncGenerator['AsyncExecutor', None]:
        """
        Context manager to handle the lifecycle of the async executor.
        """
        inst = cls()
        
        # 1. Start all background generation tasks immediately
        for target in targets:
            inst.run_async(target)
            
        # 2. Schedule the 'join' cleanup to run in the background 
        # so it pushes `None` only when all producers finish.
        cleanup_task = inst.loop.create_task(inst.join())
        
        try:
            yield inst
        finally:
            # 3. Ensure the cleanup finishes if the user exits early
            await cleanup_task
            
        
           

if __name__ == "__main__":
    
    async def worker2(name, delay):
        yield f"[{name}] initial yield"
        await asyncio.sleep(delay)
        yield f"[{name}] result after {delay} seconds"
        
    async def main():
        # Instantiate targets with fluent callback pattern
        target1 = AsyncGeneratorTarget(worker2, "agent1", 3)
        target2 = AsyncGeneratorTarget(worker2, "agent2", 1)
        
        # Fire off both targets concurrently (non-blocking)
        async with AsyncExecutor.run([target1, target2]) as executor:
            # Read results as they become available (blocking)
            async for result in executor.read_from_queue():
                print(f"Received: {result}")
     

    asyncio.run(main())
       

 
 