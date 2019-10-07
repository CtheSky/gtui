"""Task related definitions"""

class TaskStatus:
    """Enum for task status"""
    Waiting = 'Waiting'
    Running = 'Running'
    Success = 'Success'
    Failure = 'Failure'


class Task:
    """A task consists of function, its parameters and a name associated with it"""

    def __init__(self, name, func, args=(), kwargs=None):
        self.name = name
        self.func = func
        self.args = args
        self.kwargs = kwargs or {}

    def run(self):
        self.func(*self.args, **self.kwargs)

class TaskGraph:
    """A graph containing tasks and their execution dependencies"""

    def __init__(self):
        self.tasks = []
        self.task2waiting_for = {}

    def add_task(self, task: Task):
        """Add task to this graph"""
        self.tasks.append(task)
        self.task2waiting_for[task] = []

    def add_run_dependency(self, task: Task, waiting_for: Task):
        """Add execution dependency to this graph"""
        self.task2waiting_for[task].append(waiting_for)

    def run(self):
        """A hepler function to run this task graph"""
        from .visualizer import Visualizer
        Visualizer(self).run()

    @classmethod
    def linear_graph_from_list(cls, tasks):
        """A hepler function to create a graph of tasks with linear dependency"""
        graph = cls()
        for t in tasks:
            graph.add_task(t)
        for t1, t2 in zip(tasks[:-1], tasks[1:]):
            graph.add_run_dependency(t2, waiting_for=t1)
        return graph
