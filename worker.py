"""
 Copyright (c) 2023 Anthony Mugendi
 
 This software is released under the MIT License.
 https://opensource.org/licenses/MIT
"""
import asyncio
from classwork import ClassWork


class WorkerClass:
    # your worker...
    async def add(self, a, b):
        # the work!
        resp = a + b
        # this is a long process
        await asyncio.sleep(3)
        return resp

    async def analyze_arr(self, arr):
        print(arr)

        return arr


# this is our nats server url
nats_url = "nats://127.0.0.1:4222"
# initialize ClassWork
class_work = ClassWork(nats_url=nats_url)
# init worker class
worker = WorkerClass()

# Ok, let us register things with asyncio
asyncio.run(class_work.register(name="my-worker", worker_class=worker))
