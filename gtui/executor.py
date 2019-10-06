"""
An executor to run the task graph.

It uses mutli-threading to schedule and run the taks according to
their dependencies defined in the task graph.

Each task is binded to a thread. The output and log records of each
thread are collected separatedly. The visualizer will query the executor
and display these information in TUI to let user know what is going on.
"""
import io
import sys
import logging
import traceback
import threading

from .utils.werkzeug_local import Local, LocalProxy
from .task import Task, TaskGraph, TaskStatus

_local = Local()
sys.stdout = LocalProxy(lambda: getattr(_local, 'stdout', sys.__stdout__))


class IORedirectedThread(threading.Thread):
    """A Thread subclass which replace the sys.stdout with a StringIO when running"""

    def __init__(self, group=None, target=None, name=None, args=(), kwargs=None, *,
                 daemon=None, callback=None, callback_args=(), callback_kwargs=None):
        super().__init__(group, target, name, args, kwargs, daemon=daemon)
        self.parent = threading.current_thread()
        self.error = None
        self.traceback = None
        self.str_stdout = io.StringIO()
        self.callback = callback
        self.callback_args = callback_args
        self.callback_kwargs = callback_kwargs or {}

    def run(self):
        setattr(_local, 'stdout', self.str_stdout)
        try:
            threading.Thread.run(self)
        except BaseException as e:
            self.error = e
            self.traceback = traceback.format_exc()

        if self.error:
            logging.debug('Thread %s exit with error %s traceback: %s',
                          self.name, self.error, self.traceback)

        if self.callback:
            self.execute_callback_in_new_thread()

    def execute_callback_in_new_thread(self):
        def wait_and_execute(thread: IORedirectedThread):
            thread.join()
            thread.callback(*thread.callback_args, **thread.callback_kwargs)

        thread = threading.Thread(
            target=wait_and_execute,
            args=(self,),
            daemon=True
        )
        thread.start()

    def get_stdout_content(self):
        return self.str_stdout.getvalue()

class SeparateThreadLogCollector:
    """Register log handler. Separate & collect logs for each thread."""

    name2records = {}

    @classmethod
    def init_log_setting(cls):
        class SeparateByThreadNameHandler(logging.Handler):
            def emit(self, record: logging.LogRecord):
                cls.name2records.setdefault(record.threadName, [])
                cls.name2records[record.threadName].append(record)

        logging.root.handlers = []
        logging.root.addHandler(SeparateByThreadNameHandler())
        logging.root.setLevel(logging.DEBUG)

    @classmethod
    def get_thread_log_records(cls, name):
        return cls.name2records.get(name, [])

    @classmethod
    def get_main_thread_log_records(cls):
        return cls.name2records.get(threading.main_thread().name, [])


class Executor:
    """Given a TaskGraph, schedule & run & record log of the tasks. Using mutlithreading."""

    def __init__(self, graph: TaskGraph, callback=None):
        """Initialize an executor with a task graph and an optional callback functon

        Parameters
        ----------
        graph : TaskGraph
            A TaskGraph object containing tasks and their dependencies.

        callback : function
            A function which accepts a boolean as parameter. It will be called with True
            if execution succeeds and with False if execution fails. One can send an email,
            a desktop notification or other things to inform user of the execution result.
        """
        self.graph = graph
        self.callback = callback
        self.log_collector = SeparateThreadLogCollector
        self.task2thread = {
            task:IORedirectedThread(
                target=task.run,
                name=task.name,
                callback=self.check_finish_status_and_schedule_task_to_run,
                daemon=True
            ) for task in graph.tasks
        }
        self.thread2started = {thread: False for thread in self.task2thread.values()}
        self.thread_start_lock = threading.RLock()

    def start_execution(self):
        self.log_collector.init_log_setting()
        with self.thread_start_lock:
            for task in self.get_tasks_ready_to_run():
                thread = self.task2thread[task]
                thread.start()
                self.thread2started[thread] = True

    def check_finish_status_and_schedule_task_to_run(self):
        if self.if_any_failed_task() and self.callback:
            self.callback(False)

        if self.if_all_tasks_success() and self.callback:
            self.callback(True)

        with self.thread_start_lock:
            for task in self.get_tasks_ready_to_run():
                thread = self.task2thread[task]
                thread.start()
                self.thread2started[thread] = True

    def get_tasks_ready_to_run(self):
        ready_tasks = [
            task
            for task, waiting_for in self.graph.task2waiting_for.items()
            if self.get_task_status(task) == TaskStatus.Waiting and self.if_all_tasks_success(waiting_for)
        ]
        return ready_tasks

    def get_task_output(self, task: Task):
        return self.task2thread[task].get_stdout_content()

    def get_task_thread(self, task: Task):
        return self.task2thread[task]

    def get_task_status(self, task: Task):
        thread = self.get_task_thread(task)
        if thread.is_alive():
            return TaskStatus.Running
        if not self.thread2started[thread]:
            return TaskStatus.Waiting
        if thread.error:
            return TaskStatus.Failure
        return TaskStatus.Success

    def if_all_tasks_success(self, tasks=None):
        if tasks is None:
            tasks = self.graph.tasks
        return all([self.get_task_status(t) == TaskStatus.Success for t in tasks])

    def if_any_failed_task(self):
        return any([self.get_task_status(t) == TaskStatus.Failure for t in self.graph.tasks])
