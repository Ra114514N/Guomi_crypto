#!/usr/bin/env python3
"""Tkinter GUI for the envelope protocol demo."""

from __future__ import annotations

import logging
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from tkinter.scrolledtext import ScrolledText

sys.path.insert(0, str(Path(__file__).parent))

ARTIFACTS = Path(__file__).parent / "artifacts"
DEFAULT_PLAIN = Path(__file__).parent / "plain.txt"
DEFAULT_SENDER_ID = "sender@sm9.local"


class QueueHandler(logging.Handler):
    def __init__(self, q: queue.Queue[str]):
        super().__init__()
        self.q = q

    def emit(self, record):
        self.q.put(self.format(record))


class EnvTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.text = ScrolledText(self, height=18)
        self.text.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        ttk.Button(self, text="Refresh", command=self.refresh).pack(pady=(0, 10))
        self.refresh()

    def refresh(self):
        from crypto.gmssl_loader import error_message, is_available

        lines = [
            f"Python: {sys.version.split()[0]}",
            "Protocol: envelope v3.0",
            "SM2: sm2_wrap",
            "SM4: CBC / CTR / GCM",
            "ZUC-128: enabled",
            f"SM9 native library: {'available' if is_available() else 'unavailable - ' + error_message()}",
        ]
        self.text.delete("1.0", tk.END)
        self.text.insert(tk.END, "\n".join(lines))


class DemoTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.running = False
        self.q: queue.Queue[str] = queue.Queue()
        self.handler: QueueHandler | None = None

        top = ttk.Frame(self)
        top.pack(fill=tk.X, padx=10, pady=10)
        self.algo = tk.StringVar(value="sm4-gcm")
        ttk.Combobox(top, textvariable=self.algo, values=["sm4-gcm", "sm4-cbc", "sm4-ctr", "zuc"], state="readonly", width=12).pack(side=tk.LEFT)
        self.file = tk.StringVar(value=str(DEFAULT_PLAIN))
        ttk.Entry(top, textvariable=self.file).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=8)
        ttk.Button(top, text="Browse", command=self.browse).pack(side=tk.LEFT)
        self.button = ttk.Button(top, text="Run Demo", command=self.start)
        self.button.pack(side=tk.LEFT, padx=(8, 0))

        self.out = ScrolledText(self, height=24)
        self.out.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def browse(self):
        path = filedialog.askopenfilename(title="Select plaintext")
        if path:
            self.file.set(path)

    def append(self, text: str):
        self.out.insert(tk.END, text + "\n")
        self.out.see(tk.END)

    def parse_algo(self):
        value = self.algo.get()
        if value == "zuc":
            return "zuc", "cbc"
        return "sm4", value.split("-")[1]

    def start(self):
        path = Path(self.file.get())
        if not path.exists():
            messagebox.showerror("Error", f"Plaintext file not found: {path}")
            return
        if self.running:
            return
        self.running = True
        self.button.configure(state=tk.DISABLED)
        self.out.delete("1.0", tk.END)
        self.q = queue.Queue()
        self.handler = QueueHandler(self.q)
        self.handler.setFormatter(logging.Formatter("%(message)s"))
        logging.getLogger().addHandler(self.handler)
        self.after(100, self.poll)
        threading.Thread(target=self.run, args=(path,), daemon=True).start()

    def poll(self):
        while not self.q.empty():
            self.append(self.q.get())
        if self.running:
            self.after(100, self.poll)

    def run(self, path: Path):
        try:
            from core.workflow import run_full_workflow

            cipher, mode = self.parse_algo()
            result = run_full_workflow(path, cipher=cipher, mode=mode, output_dir=ARTIFACTS)
            self.after(0, self.done, result, None)
        except Exception as exc:
            self.after(0, self.done, None, exc)

    def done(self, result, error):
        if self.handler:
            logging.getLogger().removeHandler(self.handler)
            self.handler = None
        self.poll()
        if error:
            self.append(f"\nError: {error}")
        else:
            send = result["send"]
            recv = result["receive"]
            self.append("\n=== Result ===")
            self.append(f"Algorithm: {send['algo_label']}")
            self.append(f"Auth tag: {send['auth_tag'][:32]}...")
            self.append(f"Signature: {send['signature_hex'][:32]}...")
            self.append(f"Integrity: {'OK' if recv['integrity_ok'] else 'FAIL'}")
            self.append(f"Signature verify: {'OK' if recv['signature_ok'] else 'FAIL'}")
            self.append(f"Digest: {'OK' if recv['digest_ok'] else 'FAIL'}")
            self.append(f"Envelope: {ARTIFACTS / 'message.json'}")
        self.running = False
        self.button.configure(state=tk.NORMAL)


class SendReceiveTab(DemoTab):
    def __init__(self, parent):
        super().__init__(parent)
        self.button.configure(text="Send + Receive")


class BenchmarkTab(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.button = ttk.Button(self, text="Run Benchmark", command=self.start)
        self.button.pack(padx=10, pady=10, anchor=tk.W)
        self.out = ScrolledText(self, height=24)
        self.out.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

    def start(self):
        self.button.configure(state=tk.DISABLED)
        self.out.delete("1.0", tk.END)
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        try:
            from core.benchmark import run_benchmark

            md = run_benchmark(output_dir=ARTIFACTS)
            self.after(0, self.done, md, None)
        except Exception as exc:
            self.after(0, self.done, None, exc)

    def done(self, md, error):
        self.out.insert(tk.END, f"Error: {error}" if error else md)
        self.button.configure(state=tk.NORMAL)


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("国密安全传输系统")
        self.geometry("900x650")
        nb = ttk.Notebook(self)
        nb.pack(fill=tk.BOTH, expand=True)
        nb.add(EnvTab(nb), text="Environment")
        nb.add(DemoTab(nb), text="Demo")
        nb.add(SendReceiveTab(nb), text="Send/Receive")
        nb.add(BenchmarkTab(nb), text="Benchmark")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")
    App().mainloop()
