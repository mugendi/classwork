<!--
 Copyright (c) 2023 Anthony Mugendi
 
 This software is released under the MIT License.
 https://opensource.org/licenses/MIT
-->

# Classwork

This is a simple Python module to help distribute you tasks across multiple brokers as microservices.

Classwork uses [NATS](https://nats.io/) to manage communication between job schedulers and workers. Nats does most of the heavy lifting, allowing us to keep the rest of the code simple and concise.

## What is in name?
So why ClassWork? 
Well, this is simply because workers are simply **"python classes"** (The Class) whose **"methods"** become individual workers (The Students). 

## Get started

First let us create a simple worker

```python
import asyncio
from classwork import ClassWork


class WorkerClass:
    # Your worker...
    # Notice that we expect workers to be async
    async def add(self, a, b):
        # the work!
        resp = a + b
        # simulate a long process
        await asyncio.sleep(3)
        # return results
        return resp


# this is our nats server url
nats_url = "nats://127.0.0.1:4222"
# initialize ClassWork
class_work = ClassWork(nats_url=nats_url)
# init worker class
worker = WorkerClass()

# Ok, let us register things with asyncio
# notice the method 'class_work.register' is async!
asyncio.run(class_work.register(name="my-worker", worker_class=worker))

```

This is all the code we need to set up the worker.
It is important to note the following:

1. Worker Class methods should be asynchronous
2. class_work.register is also async
3. You will need NATS running with [JetStream](https://docs.nats.io/nats-concepts/jetstream) enabled!

## The Job Scheduler

Now we need to create the job scheduler. Below is the code we need

```python
import asyncio
import numpy as np
from pprint import pprint
from classwork import ClassWork

# init ClassWork
nats_url = "nats://127.0.0.1:4222"
class_work = ClassWork(nats_url=nats_url)

# Our callback function
# This is where complete work gets reported
def report_callback(report_card):
    print("We have a report!")
    pprint(report_card)


# We need this function to create our job schedules
async def schedules():
    # Assign a job
    await class_work.assign(
        # the task name
        task="my_worker.add",
        # arguments
        args=[1, 2],
        # the callback to report our results
        report_callback=report_callback,
    )


# Ok, let us create the schedules now
asyncio.run(schedules())
```

This code will create a *task* into NATS and the job workers (attentive students 😂) already listening will pick the task and run it, then publish their reports which is routed via NATS back to the scheduler (teacher?).

Take note of the following:
1. `class_work.assign` must be run in async mode. So we have wrapped it in an async method. You can also use `asyncio.run` directly.
2. Naming your task is very important. This naming convection is unashamedly borrowed from [moleculer](https://moleculer.services/). In this case, your task is **"my_worker.add"**. This will route to any worker class registered with the **name** "my_worker" and method "add". 
3. Because all this traffic is routed via NATS, your arguments must be JSON serializable. Even though we use [typ](https://github.com/vsapronov/typjson) to handle edge cases like `sets`, beware that there are limits to what you can pass in your arguments
4. `report_callback` is called with a 'report' of your task. A report card 😊 will look like the one below:


```
We have a report!
{'task': 'my_worker.add',
 'duration': {'latency': {'request': '4 ms and 356 µs',
                          'response': '5 s and 4 ms'},
              'my_worker.add': '3 s and 1 ms'},
 'req_id': '8mYjJjM0kb5',
 'response': 3}
```

## Report Explanation
- **duration:** is a high precision (down to yoctoseconds) report of the time taken.
    - **latency:** shows the time taken to route your "task **request**" to the worker and "task **response**" back to the scheduler.
- **req_id:** is a unique id assigned to each job
- **response:** is the actual value returned by the worker


## Try it

We have sample code in [scheduler.py](scheduler.py) and [worker.py](worker.py)