from typing import Optional


class Logger:
    def __init__(self, verbose=False):
        self.verbose = verbose
        print(f"Logger initialized {"--verbose" if verbose==True else ""}")
    
    def print(self, *args, **kwargs) -> None:
        print(*args, **kwargs)

    def vprint(self, *args, **kwargs) -> None:
        if self.verbose:
            print(*args, **kwargs)

    @staticmethod
    def initialize(verbose=False) -> None:
        global _logger
        _logger = Logger(verbose)


_logger: Optional[Logger] = None


def log() -> Logger:
    if _logger is None:
        raise RuntimeError("Logger not initialized — call core.logger.set_logger(...) from main")
    return _logger