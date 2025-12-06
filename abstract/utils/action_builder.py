from component.direction import Direction
from component.action import Action

class ActionBuilder:
    def __init__(self, agent):
        self.agent = agent

    def move(self, direction: Direction):
        return Action("move", self.agent, {"direction": direction})

    def interact(self, target_id):
        return Action("interact", self.agent, {"target": target_id})

    def pick(self):
        return Action("pick", self.agent, {})

    def drop(self, item_id):
        return Action("drop", self.agent, {"item": item_id})

    def wait(self):
        return Action("wait", self.agent, {})