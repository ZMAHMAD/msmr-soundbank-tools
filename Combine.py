import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import scrolledtext

# This file lives in the project root, next to the Banks / WEMs / WAVs folders.
BASE = Path(__file__).resolve().parent
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)

# (button label, script file, command builder)
STEPS = [
    ("1. Extract soundbanks", "soundbank_extractor.py", lambda p: [sys.executable, "-u", str(p)]),
    ("2. Convert banks", "bnkconverter.bat", lambda p: ["cmd", "/c", str(p)]),
    ("3. Convert WEMs", "wemconverter.bat", lambda p: ["cmd", "/c", str(p)]),
]

# Folder holding soundbank_extractor.py and the .bat files.
SCRIPTS_DIR = BASE / "src"

COUNT_FOLDERS = [
    ("Soundbanks", BASE / "Soundbanks", ".soundbank"),
    ("Banks", BASE / "Banks", ".bnk"),
    ("WEMs", BASE / "WEMs", ".wem"),
    ("WAVs", BASE / "WAVs", ".wav"),
]


def count_files(folder: Path, ext: str) -> int | None:
    if not folder.is_dir():
        return None
    total = 0
    for _, _, files in os.walk(folder):
        total += sum(1 for f in files if f.lower().endswith(ext))
    return total


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Soundbank Pipeline")
        self.geometry("760x560")

        self.msgs: queue.Queue = queue.Queue()
        self.proc: subprocess.Popen | None = None
        self.running = False
        self.stop_requested = False

        self._build_ui()
        self.refresh_counts()
        self.after(100, self._poll)
        self.after(1500, self._tick)
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ---------- UI ----------
    def _build_ui(self):
        counts = tk.LabelFrame(self, text="File counts", padx=10, pady=8)
        counts.pack(fill="x", padx=10, pady=(10, 5))
        self.count_labels = {}
        for i, (label, _, ext) in enumerate(COUNT_FOLDERS):
            cell = tk.Frame(counts)
            cell.grid(row=0, column=i, padx=18)
            num = tk.Label(cell, text="-", font=("Segoe UI", 20, "bold"))
            num.pack()
            tk.Label(cell, text=f"{label}\n({ext})").pack()
            self.count_labels[label] = num
        for i in range(len(COUNT_FOLDERS)):
            counts.columnconfigure(i, weight=1)

        buttons = tk.Frame(self)
        buttons.pack(fill="x", padx=10, pady=5)
        self.step_buttons = []
        for i, (label, _, _) in enumerate(STEPS):
            b = tk.Button(buttons, text=label, command=lambda i=i: self.start([i]))
            b.pack(side="left", padx=3, expand=True, fill="x")
            self.step_buttons.append(b)

        row2 = tk.Frame(self)
        row2.pack(fill="x", padx=10, pady=(0, 5))
        self.run_all_btn = tk.Button(
            row2, text="Run all in order", bg="#2e7d32", fg="white",
            command=lambda: self.start(list(range(len(STEPS)))),
        )
        self.run_all_btn.pack(side="left", padx=3, expand=True, fill="x")
        self.stop_btn = tk.Button(row2, text="Stop", state="disabled", command=self.stop)
        self.stop_btn.pack(side="left", padx=3)
        self.refresh_btn = tk.Button(row2, text="Refresh counts", command=self.refresh_counts)
        self.refresh_btn.pack(side="left", padx=3)

        self.status = tk.Label(self, text="Idle", anchor="w")
        self.status.pack(fill="x", padx=12)

        self.log = scrolledtext.ScrolledText(self, height=15, state="disabled", font=("Consolas", 9))
        self.log.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _set_running(self, running: bool):
        self.running = running
        state = "disabled" if running else "normal"
        for b in self.step_buttons + [self.run_all_btn]:
            b.config(state=state)
        self.stop_btn.config(state="normal" if running else "disabled")

    def _log(self, text: str):
        self.log.config(state="normal")
        self.log.insert("end", text if text.endswith("\n") else text + "\n")
        self.log.see("end")
        self.log.config(state="disabled")

    # ---------- counts ----------
    def refresh_counts(self):
        for label, folder, ext in COUNT_FOLDERS:
            n = count_files(folder, ext)
            self.count_labels[label].config(text="n/a" if n is None else f"{n:,}")

    def _tick(self):
        if self.running:
            self.refresh_counts()
        self.after(1500, self._tick)

    # ---------- running steps ----------
    def start(self, indices: list[int]):
        if self.running:
            return
        self.stop_requested = False
        self._set_running(True)
        threading.Thread(target=self._worker, args=(indices,), daemon=True).start()

    def stop(self):
        self.stop_requested = True
        if self.proc and self.proc.poll() is None:
            # /T kills the whole tree (cmd + the tools it launched)
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(self.proc.pid)],
                           capture_output=True, creationflags=NO_WINDOW)

    def _worker(self, indices: list[int]):
        put = self.msgs.put
        for n, idx in enumerate(indices):
            label, filename, build = STEPS[idx]
            script = SCRIPTS_DIR / filename
            put(("status", f"Running: {label}"))
            put(("log", f"\n===== {label} =====\n"))

            if not script.is_file():
                put(("log", f"[ERROR] Could not find {script}\n"
                            "        Check that the scripts are in the src folder next to this file.\n"))
                put(("status", f"Failed: {label} (script not found)"))
                break

            env = dict(os.environ, PYTHONIOENCODING="utf-8", PYTHONUNBUFFERED="1")
            try:
                self.proc = subprocess.Popen(
                    build(script), cwd=SCRIPTS_DIR, env=env,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                    text=True, encoding="utf-8", errors="replace", bufsize=1,
                    creationflags=NO_WINDOW,
                )
                # Feed the "press any key" prompts in the .bat files.
                try:
                    self.proc.stdin.write("\n" * 20)
                    self.proc.stdin.close()
                except OSError:
                    pass
                for line in self.proc.stdout:
                    put(("log", line))
                code = self.proc.wait()
            except OSError as e:
                put(("log", f"[ERROR] Could not start {filename}: {e}\n"))
                put(("status", f"Failed: {label}"))
                break

            if self.stop_requested:
                put(("log", "[STOPPED]\n"))
                put(("status", "Stopped"))
                break
            if code != 0:
                put(("log", f"[ERROR] {filename} exited with code {code}\n"))
                put(("status", f"Failed: {label} (exit code {code})"))
                break
            put(("log", f"[OK] {label} finished\n"))
            put(("counts", None))
        else:
            put(("status", "All selected steps finished"))

        put(("done", None))

    def _poll(self):
        try:
            while True:
                kind, value = self.msgs.get_nowait()
                if kind == "log":
                    self._log(value)
                elif kind == "status":
                    self.status.config(text=value)
                elif kind == "counts":
                    self.refresh_counts()
                elif kind == "done":
                    self.refresh_counts()
                    self._set_running(False)
        except queue.Empty:
            pass
        self.after(100, self._poll)

    def _on_close(self):
        if self.running:
            self.stop()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()