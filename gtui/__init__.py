"""Simple Job Scheduler With Friendly Text User Interface"""
from .task import Task, TaskGraph
from .executor import IORedirectedThread
from . import callback

__version__ = '0.1.0'
