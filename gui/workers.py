"""QThread workers that bridge business logic to the GUI via Signals."""

import logging
from pathlib import Path

from PySide6.QtCore import QThread, Signal


class SignalHandler(logging.Handler):
    """Routes logging output to a Qt Signal for real-time log display."""

    def __init__(self, signal: Signal):
        super().__init__()
        self._signal = signal

    def emit(self, record):
        self._signal.emit(self.format(record))


ARTIFACTS = Path(__file__).resolve().parent.parent / "artifacts"


class WorkflowWorker(QThread):
    """Runs core.workflow.run_full_workflow() in a background thread."""

    progress = Signal(str)
    finished = Signal(dict)
    error = Signal(str)

    def __init__(self, plaintext_path: str, cipher: str, mode: str,
                 sender_id: str = "sender@sm9.local", parent=None):
        super().__init__(parent)
        self._path = plaintext_path
        self._cipher = cipher
        self._mode = mode
        self._sender_id = sender_id

    def run(self):
        handler = SignalHandler(self.progress)
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            from core.workflow import run_full_workflow
            result = run_full_workflow(
                self._path,
                cipher=self._cipher,
                mode=self._mode,
                sender_id=self._sender_id,
                output_dir=ARTIFACTS,
            )
            self.finished.emit(result)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            root_logger.removeHandler(handler)


class BenchmarkWorker(QThread):
    """Runs core.benchmark.run_benchmark() in a background thread."""

    progress = Signal(str)
    finished = Signal(str)
    error = Signal(str)

    def run(self):
        handler = SignalHandler(self.progress)
        handler.setFormatter(logging.Formatter("[%(levelname)s] %(message)s"))
        root_logger = logging.getLogger()
        root_logger.addHandler(handler)
        try:
            from core.benchmark import run_benchmark
            md = run_benchmark(output_dir=ARTIFACTS)
            self.finished.emit(md)
        except Exception as exc:
            self.error.emit(str(exc))
        finally:
            root_logger.removeHandler(handler)
