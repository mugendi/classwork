"""
 Copyright (c) 2023 Anthony Mugendi
 
 This software is released under the MIT License.
 https://opensource.org/licenses/MIT
"""
import json
import asyncio
import uuid
import nats

from time import perf_counter as pc
from typ import json as safe_json
from nats.aio.client import Client as NATS
from nats.aio.errors import ErrNoServers, ErrTimeout
from yachalk import chalk

from .utils import hash_str, precision_format_time, importing_script, sanitize_name, get_class_props, RaisingThread, trace_caller

app_name = "classwork"


class ClassWork:
    def __init__(self, nats_url) -> None:
        self.nats_url = nats_url
        self.busy_status = {}
        self.streams = {}

        asyncio.run(self.__setup())

    async def __setup(self):
        mac_id = hex(uuid.getnode())
        exec_file = importing_script()
        hashid = hash_str(f"{exec_file}")
        self.id = f"{app_name}_{mac_id}_{str(hashid)}"

    def __log(self, level="info", *args):
        id = self.id.replace(f"{app_name}_", "")

        level = level.upper()

        prefix = f"[{level}][{id}]"
        clr = chalk.gray

        if level in ["SUCCESS"]:
            clr = chalk.green
            prefix = chalk.bold.green("✔ " + prefix)
        if level in ["ERROR"]:
            clr = chalk.red
            prefix = chalk.bold.red("✘ " + prefix)
        if level in ["WARNING"]:
            clr = chalk.yellow
            prefix = chalk.bold.yellow("⚠ " + prefix)
        elif level in ["INFO"]:
            clr = chalk.blue
            prefix = chalk.bold.blue(prefix)

        args = list(map(lambda arg: clr(str(arg)), args))

        print("", prefix, *args)

    async def __connect(self):       
        
        # trace_caller()
    
        # Setup pool of servers from a NATS cluster.
        options = {
            "servers": self.nats_url
            if isinstance(self.nats_url, list)
            else [self.nats_url]
        }

        # Will try to connect to servers in order of configuration,
        # by defaults it connect to one in the pool randomly.
        options["dont_randomize"] = True

        # Optionally set reconnect wait and max reconnect attempts.
        # This example means 10 seconds total per backend.
        options["max_reconnect_attempts"] = 100
        options["reconnect_time_wait"] = 2

        async def disconnected_cb():
            print("Got disconnected!")

        async def reconnected_cb():
            print("Got reconnected to NATS...")

        async def error_cb(e):
            print(f"There was an error: {e}")

        async def closed_cb():
            print("Connection is closed")

        async def subscribe_handler(msg):
            print("Got message: ", msg.subject, msg.reply, msg.data)

        # Setup callbacks to be notified on disconnects and reconnects
        options["disconnected_cb"] = disconnected_cb
        options["reconnected_cb"] = reconnected_cb
        # Setup callbacks to be notified when there is an error
        # or connection is closed.
        options["error_cb"] = error_cb
        options["closed_cb"] = closed_cb

        try:
            nc = await nats.connect(**options)
        except ErrNoServers as e:
            # Could not connect to any server in the cluster.
            # print(e)
            return

        if nc.is_connected:
            # print(nc.connected_url)
            self.__log("info", f"Successfully connected : {nc.connected_url.netloc}")
            self.nc = nc
            self.js = nc.jetstream()

            return self.nc, self.js
        

    async def __add_stream(self, stream_name, subjects):
        # print(f"{stream_name=}, {subjects=}")
        # await self.__setup()
        # connect
        # nc, js = await self.__connect()
        streams = None

        try:
            # if we have already checked streams recently
            if "streams" in self.streams:
                # if checked recently
                duration_since_check = pc() - self.streams["last_check"]
                # if checked recently
                if duration_since_check < 2:
                    # reset streams
                    streams = self.streams["streams"]

            # check streams
            if not streams:
                # print("Fetching streams....")
                # get streams
                streams = await self.js.streams_info()

                self.streams = {"streams": streams, "last_check": pc()}

            if streams and len(streams):
                # loop through streams
                for stream in streams:
                    # loop through the current subjects
                    for subject in subjects:
                        # print(stream)
                        # ensure no other stream has the exact same subjects
                        if (
                            subject in stream.config.subjects
                            and stream_name != stream.config.name
                        ):
                            # print(stream.config.subjects, subjects)
                            print("Delete stream: ", stream.config.name)

                            # do we remove or update?
                            # Better to delete
                            # stream.config.subjects.remove(subject)
                            # print(subject, stream.config.subjects)

                            # if has similar subjects, delete stream
                            await self.js.delete_stream(name=stream.config.name)

            ack = await self.js.add_stream(name=stream_name, subjects=subjects)
            # print(ack)

        except Exception as e:
            # if stream config has changed (err_code == 10058)
            # we must update the stream
            if hasattr(e, "err_code") and e.err_code == 10058:
                print("upgrade stream")
                # update_stream
                await self.js.update_stream(name=stream_name, subjects=subjects)
            else:
                raise e

    async def __clear_streams(self):
        # first connect
        nc, js = await self.__connect()

        try:
            # get streams
            streams = await js.streams_info()

            print(f"Found {len(streams)} streams...")

            # loop through streams
            for stream in streams:
                if stream.config.name.startswith(f"{app_name}_"):
                    print("deleting stream", stream.config.name)
                    await js.delete_stream(name=stream.config.name)

        except:
            pass

    def __get_messages_bg(self, subject, cb):
        asyncio.run(self.__get_messages(subject, cb))

    async def __get_messages(self, subject, cb):
        
        # _, self.jss = await connect_client(self.nats_url)
        await self.__connect()

        psub = await self.js.pull_subscribe(subject, "psub")

        # Fetch and ack messagess from consumer.
        while True:
            try:
                busy = subject in self.busy_status and self.busy_status[subject] == True

                # only fetch messages if we are not busy....
                if busy:
                    await asyncio.sleep(1)
                    continue

                msgs = await psub.fetch(1)

                # we got some messages, indicate that we are busy
                self.busy_status[subject] = True

                for msg in msgs:
                    await cb(msg)

                # seems we are done, set busy to false
                self.busy_status[subject] = False

            except Exception as e:
                # print(e)
                await asyncio.sleep(2)
                pass

    async def register(self, name, worker_class):
        await self.__setup()
        # make & sanitize name
        name = sanitize_name(name)
        # make subjects
        subjects = [f"{name}.{prop}" for prop in get_class_props(worker_class)]

        # print(subjects)
        # listen for any of these subjects
        # print(self.js)
        if not hasattr(self, "js"):
            await self.__connect()

        async def handle_message(msg):
            subject = msg.subject
            data = json.loads(msg.data.decode())
            _, prop = subject.split(".")
            func = getattr(worker_class, prop)

            # calc latency
            latency = pc() - data["call_start"]
            # call worker method and pass args
            response = await func(*data["args"])
            # calculate total time
            duration = pc() - data["call_start"] - latency

            # compose payload
            payload = {
                "response": response,
                "task": subject,
                # "args": data["args"],
                "req_id": data["req_id"],
                "call_start": data["call_start"],
                "duration": {
                    "latency": {"request": latency},
                    f"{subject}": precision_format_time(duration),
                },
            }

            ack = await self.js.publish(
                data["reply"], safe_json.dumps(payload).encode()
            )

            # acknowledge msg receipt
            await msg.ack()

        for i, subject in enumerate(subjects):
            # make stream name
            stream_name = f"{app_name}_worker_" + hash_str(f"{name}_{subject}")

            # make stream
            await self.__add_stream(stream_name=stream_name, subjects=[subject])
            
            
            t = RaisingThread(
                target=self.__get_messages_bg, args=[subject, handle_message]
            )
            t.start()

            # try:
            #     t.join()
            # except Exception as e:
            #     print(e)
            #     raise e

    async def assign(self, task, args, report_callback):
        await self.__setup()

        # make req_id
        req_id = str(pc())
        req_id = "{}_{}_{}_{}".format(
            self.id, req_id, task, "".join(list(map(str, args)))
        )
        req_id = hash_str(req_id)

        # print("call", req_id, task, args)
        payload = {
            "req_id": req_id,
            "task": task,
            "args": args,
            "call_start": pc(),
            "duration": {},
            "reply": self.id,
        }

        # connect if need be
        if not hasattr(self, "js"):
            await self.__connect()

        await self.__add_stream(stream_name=self.id, subjects=[self.id])

        ack = await self.js.publish(task, safe_json.dumps(payload).encode())
        # print(ack)
        
        async def handle_message(msg):
            
            try:
                # print(msg)
                if report_callback and callable(report_callback):
                    # subject = msg.subject
                    data = json.loads(msg.data.decode())
                    
                    # data["duration"]["request_latency"]
                    data["duration"]["latency"]["response"] = precision_format_time(
                        pc()
                        - data["call_start"]
                        - data["duration"]["latency"]["request"]
                    )
                    
                    
                    # print( data["duration"]["latency"]["request"] )

                    data["duration"]["latency"]["request"] = precision_format_time(
                        data["duration"]["latency"]["request"]
                    )

                    del data["call_start"]

                    report_callback(data)

                    # acknowledge receipt
                    await msg.ack()

            except Exception as e:
                # print(e)
                raise e

            
        t = RaisingThread(target=self.__get_messages_bg, args=[self.id, handle_message])
        t.start()
        
        

        # await __clear_streams()
