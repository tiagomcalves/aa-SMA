from __future__ import annotations

import threading
import time
import logging

from fastapi import FastAPI
import uvicorn

from owlready2 import World, Ontology
from abstract.utils import *
from abstract import Agent


class Responder(Agent):

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

        # Iniciar o servidor em background
        self.thread = threading.Thread(target=self._run_server, daemon=True)
        self.thread.start()

    def _run_server(self):
        logger = logging.getLogger(f"uvicorn-thread-{self.port}")
        logger.setLevel(logging.INFO)
        print(f"Running http server on host: {self.host} and on port {self.port}")
        uvicorn.run(self.app, host=self.host, port=self.port, log_config=None, log_level="info")

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

        if task_handler is None:
            return {"status": "error", "code": "error.semantic.unknown_task"}

        # Simulate work
        time.sleep(0.1)

        return {
            "status": "ok",
            "reply": {
                "performative": "inform",
                "conversation_id": msg.conversation_id,
                "in_reply_to": msg.message_id,
                "summary": str(task_handler()),
            }
        }
