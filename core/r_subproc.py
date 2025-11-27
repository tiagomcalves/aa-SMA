# core/renderer.py
import tkinter as tk
import tkinter.font as tkFont
import threading
import sys
import queue

def read_stdin(q):
    """ Reads stdin in a background thread to avoid blocking the Tk loop. """
    for line in sys.stdin:
        q.put(line.rstrip("\n"))

def main():
    root = tk.Tk()
    root.title("Renderer Terminal")

    font = tkFont.Font(family="Courier", size=12)   #monospaced font

    text = tk.Text(
        root,
        bg="black",
        fg="white",
        insertbackground="white",
        font=font,
        wrap="none",
        borderwidth=0,
        highlightthickness=0
    )
    text.pack(expand=True, fill="both")

    def ignore_event(event):    # every user input will be handled, ignore everything
        return "break"          # Tkinter specific

    for seq in ["<Key>", "<BackSpace>", "<Delete>", "<Return>", "<Control-v>",
                "<Control-c>", "<Button-1>", "<Button-2>", "<Button-3>"]:
        text.bind(seq, ignore_event)

    text.config(state="disabled")   #text-widget set to read-only

    q = queue.Queue()   # queue incoming lines

    threading.Thread(target=read_stdin, args=(q,), daemon=True).start()

    def poll_queue():
        while True:
            try:
                line = q.get_nowait()
            except queue.Empty:
                break

            text.config(state="normal")

            if line == "__CLEAR_SCREEN__":
                text.delete("1.0", "end")
            else:
                text.insert("end", line + "\n")

            text.see("end")
            text.config(state="disabled")

        root.after(30, poll_queue)

    poll_queue()
    root.mainloop()

if __name__ == "__main__":
    main()
