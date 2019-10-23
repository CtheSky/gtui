"""Simple Job Scheduler With Friendly Text User Interface"""
from .task import Task, TaskGraph
from .executor import IORedirectedThread

__version__ = '0.0.1'
