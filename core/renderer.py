import subprocess

class Renderer:
    def __init__(self):
        self._p = subprocess.Popen(
            ["python", "core/r_subproc.py"],
            stdin=subprocess.PIPE,
            text=True,
            bufsize=1
        )

    def buffer(self, string: str):
        # Always newline-terminate
        self._p.stdin.write(string + "\n")

    def draw(self):
        self._p.stdin.flush()

    def clear(self):
        self.buffer("__CLEAR_SCREEN__")
        self.draw()