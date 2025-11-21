from __future__ import annotations

import inspect
import threading
import time
import logging
from abc import abstractmethod

from fastapi import FastAPI
import uvicorn

from owlready2 import World
from abstract.utils import *
from abstract import Agent


class Responder(Agent):

    @abstractmethod
    def __init__(self, name: str, properties: dict):
        super().__init__(name, properties)
        self.name = name
        self.world = World()
        self.onto = load_onto(self.name, self.world, properties["onto_file"])

        self.app = FastAPI(title=f"{self.name} server instance")
        self.host = properties["host"]
        self.port = properties["port"]
        self.app.post("/ingest")(self.ingest)  # Bind method as handler

        self.response_table = {}

        # new server thread
        self.ready_event = threading.Event()
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

    def _run_server(self):
        logger = logging.getLogger(f"uvicorn-thread-{self.port}")
        logger.setLevel(logging.INFO)

        config = uvicorn.Config(self.app, host=self.host, port=self.port, log_config=None, log_level="info")
        server = uvicorn.Server(config)

        # fires up another thread in the background and signal when ready
        loop = threading.Thread(target=server.run, daemon=True)
        loop.start()

        # wait for the http srv to be ready
        while not server.started:
            pass

        print(f"Running http server for \"{self.name}\" on host: {self.host} and on port {self.port}")
        self.ready_event.set()  # signal main thread that the server is ready
        loop.join()  # keeps main thread running

    def call_command(self, cmd_name: str, *args, **kwargs):
        """
        Chama dinamicamente a função associada a cmd_name.
        Passa args e kwargs para a função.
        """
        if cmd_name not in self.response_table:
            return "Unknown request"

        func = getattr(self, cmd_name, None)
        if func is None:
            raise ValueError(f"Comando desconhecido: {cmd_name}")

        sig = inspect.signature(func)

        # Filtrar kwargs válidos
        valid_kwargs = {k: v for k, v in kwargs.items() if k in sig.parameters}

        # Truncar args extras
        param_list = list(sig.parameters.values())
        positional_args_count = sum(1 for p in param_list if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD))
        valid_args = args[:positional_args_count]

        return func(*valid_args, **valid_kwargs)

    async def ingest(self, msg: AgentMessage):
        # Idempotency
        # if msg.idempotency_key and dedupe(msg.idempotency_key):
        # {"status": "duplicate", "message_id": msg.message_id}

        # TTL enforcement (simple)
        # In production, compare received_at - parsed timestamp.
        if msg.ttl and msg.ttl <= 0:
            return {"status": "error", "code": "error.timeout"}

        if msg.performative != "request":
            return {"status": "error", "code": "error.semantic.unknown_task"}

        received_task_string = msg.content.get("task")
        task_handler = self.response_table.get(received_task_string)
        #print("received task string: ", received_task_string)
        #print("task_handler: ", task_handler)

        if task_handler is None:
            return {"status": "error", "code": "error.semantic.unknown_task"}

        # Simulate work
        #time.sleep(0.1)

        return {
            "status": "ok",
            "reply": {
                "performative": "inform",
                "conversation_id": msg.conversation_id,
                "in_reply_to": msg.message_id,
                "summary": str(self.call_command(received_task_string,msg.content.get("args"))),
            }
        }
