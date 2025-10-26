from __future__ import annotations

import uuid
from typing import final

import datetime
import time

import requests

from env import Environment
from abstract import *
from agent import *

def now_iso():
    return datetime.datetime.now().replace(microsecond=0).isoformat() + "Z"

def compose_request(conversation_id, sender, receiver, task, args):
    return {
        "message_id": str(uuid.uuid4()),
        "conversation_id": conversation_id,
        "sender": sender,
        "receiver": receiver,
        "timestamp": now_iso(),
        "performative": "request",
        "schema_version": "1.0.0",
        "ttl": 120,
        "idempotency_key": f"{conversation_id}:{task}",
        "content": {"task": task, "args": args}
    }

def send(url, msg):
    r = requests.post(url, json=msg, timeout=10)
    r.raise_for_status()
    return r.json()

def available_lines():
    msg = compose_request(conv, "planner@svc", "researcher@svc", "available_lines", "")
    res = send("http://localhost:8000/ingest", msg)
    query_res = res.get("reply").get("summary")
    #print("\n", query_res)
    print(query_res)

def available_city_lines(input):
    msg = compose_request(conv, "planner@svc", "researcher@svc", "available_city_lines", input)
    res = send("http://localhost:8000/ingest", msg)
    query_res = res.get("reply").get("summary")
    #print("\n", query_res)
    print(query_res)

def malicious_available_lines(args):
    msg = compose_request(conv, "planner@svc", "researcher@svc", "available_lines", args)
    res = send("http://localhost:8000/ingest", msg)
    query_res = res.get("reply").get("summary")
    #print("\n", query_res)
    print(query_res)

@final
class Simulator:

    config: str
    env: Environment

    def __init__(self, file: str):
        self.agents = []
        self.curr_time = time.time()

    @staticmethod
    def create(file: str) -> Simulator:
        pass

    def list_agents(self) -> list[Agent]:
        return self.agents

    def think(self):    # execute
        pass


if __name__ == "__main__":

    conv = "conv-{}".format(int(time.time()))

    curr_agents =[]

    travel_a = Agent.create("Travel Assistant", "agents.json")
    travel_a.ready_event.wait()

    curr_agents.append(travel_a)
    env = Environment(5,curr_agents)


    while True :

        #print("My keys: ")
        print(f" :: {now_iso()}" )
        string = env.agents[0].get_name()

        print(string)   # prints "Travel Assistant"

        #if isinstance(env.agents[0], TravelAssistant):
        #    env.agents[0].available_lines()

        #render_state

        available_lines()
        available_city_lines("Lisboa")

        print("Calling \"available_lines()\" with extra parameters")

        malicious_available_lines("garbage arg, 1, 123.456")

        time.sleep(0.75)