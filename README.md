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

t1 = Task('t1', func=foo, args=[0.1])
t2 = Task('t2', func=foo, args=[1])
t3 = Task('t3', func=foo, args=[1])
t4 = Task('t4', func=foo, args=[0.5])

g = TaskGraph()
g.add_task(t1)
g.add_task(t2, waiting_for=t1)
g.add_task(t3, waiting_for=t1)
g.add_task(t4, waiting_for=[t2, t3])

g.run()
```

`TaskGraph.run` starts the text user interface, and you can navigate through tasks, see their status, output and logs:
![tui_demo.gif](https://github.com/CtheSky/gtui/blob/master/img/tui_demo.gif)

Keybindings:
* t : toggle tail -f mode, will follow text when enabled
* tab : switch between output & log
* j/k : select previous/next task
* h/l : page up/down
* ↑/↓ : scroll up/down one line
* y : copy text
* q : exit

## Task & TaskGraph

`Task` defines what to do and has an unique name:

```python
# foo(*args, **kwargs) will be called
t = Task(name='foo', func=foo, args=[1, 2], kwargs={'foo': 'bar'})
```

`TaskGraph` defines execution order of a set of tasks, it provides method to declare task & dependency:
```python
g = TaskGraph()
g.add_task(t1)                              # added task t1
g.add_task(t2, waiting_for=t1)              # added task t2, t2 runs after t1 finishes
g.add_tasks([t3, t4])                       # added task t3, t4
g.add_dependency(t3, waiting_for=[t1, t2])  # declare t3 to run after t1 & t2 finish
```

When `TaskGraph` contains a cycle denpendency, `run` method will throw a `ValueError`. You can also use `has_cycle` to 
check:

```python
> g = TaskGraph()
> g.add_tasks([t1, t2])
> g.add_dependency(t1, waiting_for=t2)
> g.add_dependency(t2, waiting_for=t1)
> g.has_cycle()
[t1, t2, t1]
```

## Run Options

`TaskGraph.run` provides some options:

```python
g.run(
  title='Demo',           # Text shown at the left bottom corner
  callback=None,          # A function called when execution fail or succeed
  log_formatter=None,     # An instance of logging.Formatter, to specify the log format
  exit_on_success=False   # whether exit tui when execution succeed
)
```

`callback` can be used to notify the execution result, it will be called with an boolean indicating whether execution succeed. `gtui.callback` has some common callbacks:

```python
# emit a desktop notification, use osascript on mac and notify-send on linux
from gtui import callback
g.run(callback.desktop_nofity(title='Plz See Here!', success_msg='Success', fail_msg='Fail'))
```

## Possible Problem with Stdout

Writing to stdout will break the TUI display. `gtui` runs each task in a new thread with `sys.stdout` replaced so functions like `print` will just work fine. When creating a new thread inside a task, `gtui.IORedirectedThread` can be used to achieve the same result:

```python
from gtui import IORedirectedThread

t = IORedirectedThread(target=print, args=['hello world'])
t.start()
t.join()

content = t.get_stdout_content()
```

However, `gtui` doesn't try to deal with other cases so you should take care of it by yourself.
