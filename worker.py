"""Compatibility shim. Real code in utils/worker.py.

Re-exports the Worker class so that
``from worker import Worker`` continues to work.
"""
from utils.worker import Worker
