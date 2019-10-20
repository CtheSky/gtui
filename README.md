## gtui

A task executor with text-based user interface, able to:

* declare task & dependency as a graph
* execute task graph
* show task status, stdout & log 
* provide a nice user interface

To install:

```
$ pip install gtui
```

## Quickstart

Let's say we have some helloworld tasks & their dependencies like this:

![task_graph_demo.png](https://github.com/CtheSky/gtui/blob/master/img/task_graph_demo.png)

We need to create `Task` and add them to `TaskGraph`:

```python
import time
import logging
from gtui import Task, TaskGraph

def foo(n):
    logging.info('foo(%s) is called', n)
    print('Start to sleep %s seconds.' % n)
    time.sleep(n)
    print('Hello World!')
    
# create tasks
t1 = Task('t1', func=foo, args=[0.1])
t2 = Task('t2', func=foo, args=[1])
t3 = Task('t3', func=foo, args=[1])
t4 = Task('t4', func=foo, args=[0.5])

# create task graph
g = TaskGraph()
g.add_tasks([t1, t2, t3, t4])
g.add_run_dependency(t2, waiting_for=t1)
g.add_run_dependency(t3, waiting_for=t1)
g.add_run_dependency(t4, waiting_for=t2)
g.add_run_dependency(t4, waiting_for=t3)

g.run()

```

`TaskGraph.run` starts the text user interface, and you can navigate through tasks, see their status, output and logs:
![tui_demo.gif](https://github.com/CtheSky/gtui/blob/master/img/tui_demo.gif)


