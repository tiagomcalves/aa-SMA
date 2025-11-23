HANDLER_REGISTRY = {}

def register_handler(name: str):
    def decorator(cls):
        HANDLER_REGISTRY[name] = cls
        return cls
    return decorator
