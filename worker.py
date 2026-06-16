"""OPAL-OKB — Worker for background computation."""
from PyQt5.QtCore import QObject, pyqtSignal
import traceback


class Worker(QObject):
    """Background computation worker.

    Runs a function in a QThread and emits signals with results.
    Usage:
        thread = QThread()
        worker = Worker(fn, *args, **kwargs)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(...)
        worker.error.connect(...)
        worker.finished.connect(thread.quit)
        thread.start()
    """
    finished = pyqtSignal(object)  # computation result
    error = pyqtSignal(str)        # error message
    progress = pyqtSignal(int)     # progress percentage (0-100)

    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            result = self.fn(*self.args, **self.kwargs)
            self.finished.emit(result)
        except Exception as e:
            self.error.emit(
                f"{type(e).__name__}: {e}\n{traceback.format_exc()}")
