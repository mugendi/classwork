"""
 Copyright (c) 2023 Anthony Mugendi
 
 This software is released under the MIT License.
 https://opensource.org/licenses/MIT
"""


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
        # the task
        task="my_worker.add",
        # arguments
        args=[1, 2],
        report_callback=report_callback,
    )

    arr = np.random.uniform(low=0.5, high=13.3, size=(2,))

    # print("resp", resp)
    await class_work.assign(
        # the task
        task="my_worker.analyze_arr",
        # arguments
        args=[arr.tolist()],
        report_callback=report_callback,
    )

# Ok, let us create the schedules now
asyncio.run(schedules())
