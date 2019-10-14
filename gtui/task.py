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

    def __repr__(self):
        return 'gtui.Task(name={}, func={!r}, args={!r}, kwargs={!r})'.format(
            self.name,
            self.func,
            self.args,
            self.kwargs
        )

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

    def run(self,
            title='Demo',
            callback=None,
            log_formatter=None):
        """A hepler function to run this task graph

        Parameters
        ----------
        title : str
            The title of TUI, will be displayed at left bottom corner.
        callback : functoin
            A function which accepts a boolean indicating whether execution succeeds.
            It will be called when execution finishes.
        log_formatter: logging.Formatter
            An instance of logging.Formatter. Defaults to gtui.utils.default_log_formatter.

        Raises
        ------
        ValueError
            If there is a cycle in graph, the message describe the cycle with task names.
        """
        from .visualizer import Visualizer
        from .utils import default_log_formatter

        if not log_formatter:
            log_formatter = default_log_formatter

        cycle = self.has_cycle()
        if cycle:
            raise ValueError('Found circle in TaskGraph: ' + ' -> '.join([t.name for t in cycle]))

        Visualizer(
            graph=self,
            title=title,
            callback=callback,
            log_formatter=log_formatter
        ).run()

    def has_cycle(self):
        """Returns a list of tasks contained in a cycle if there is one or None if no cycle."""
        cycle = None

        task2visited = {t: False for t in self.tasks}
        task2on_stack = {t: False for t in self.tasks}
        task2on_stack_dep = {t: None for t in self.tasks}

        def dfs(t):
            nonlocal cycle
            task2visited[t] = True
            task2on_stack[t] = True
            for w in self.task2waiting_for[t]:
                if cycle:
                    return
                elif not task2visited[w]:
                    task2on_stack_dep[t] = w
                    dfs(w)
                elif task2on_stack[w]:
                    cycle = []
                    v = w
                    while v != t:
                        cycle.append(v)
                        v = task2on_stack_dep[v]
                    cycle += [t, w]
            task2on_stack[t] = False

        for t in self.tasks:
            if not task2visited[t]:
                dfs(t)

        return cycle

    @classmethod
    def linear_graph_from_list(cls, tasks):
        """A hepler function to create a graph of tasks with linear dependency"""
        graph = cls()
        for t in tasks:
            graph.add_task(t)
        for t1, t2 in zip(tasks[:-1], tasks[1:]):
            graph.add_run_dependency(t2, waiting_for=t1)
        return graph
