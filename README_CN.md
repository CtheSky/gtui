## gtui

![badge>python3.4+](https://img.shields.io/badge/python-3.4%2B-blue)
![badge license GPL](https://img.shields.io/badge/license-GPL-blue)
![window not supported](https://img.shields.io/badge/windows-not%20supported-red)

一个命令行界面的任务调度 & 执行器，支持：
* 将要执行的任务和依赖关系声明成一个图
* 执行依赖关系图
* 显示任务的状态，输出和日志
* 一个友好的命令行交互界面

## Why this
平时我总是有很多脚本要跑。这些脚本执行的时候有先后的依赖关系，我希望它们可以最大程度地并行，同时又可以非常简单地去查看每个任务的执行状态，输出和日志，所以就写了这个工具。

## Installation

```
$ pip install gtui
```
Note: 不支持 window 原生终端，需要使用 cygwin 或者 wsl.

## Quickstart

假设我们有几个输出 helloworld 的任务以及对应的执行依赖关系如下图：

![task_graph_demo.png](https://github.com/CtheSky/gtui/raw/master/img/task_graph_demo.png)

我们需要创建任务 `Task` 并添加到依赖关系图 `TaskGraph` 中:

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

`TaskGraph.run` 会启动命令行界面并开始执行任务，你可以在这个界面查看任务的执行状态，输出和日志:
![tui_demo.gif](https://github.com/CtheSky/gtui/raw/master/img/tui_demo.gif)

Keybindings:
* t : 开始/关闭 tail -f 模式，自动翻页到最近的输出
* tab : 切换显示输出/日志
* j/k : 选择上/下一个任务
* h/l : 向上/下翻页
* ↑/↓ : 向上/下移动一行
* y : 复制输出到剪贴板
* q : 退出

## Task & TaskGraph

`Task` 定义了一个任务需要做什么，名称唯一:

```python
# foo(*args, **kwargs) will be called
t = Task(name='foo', func=foo, args=[1, 2], kwargs={'foo': 'bar'})
```

`TaskGraph` 定义了要执行的任务以及执行的顺序，它提供一些声明任务和依赖关系的方法:
```python
g = TaskGraph()
g.add_task(t1)                              # added task t1
g.add_task(t2, waiting_for=t1)              # added task t2, t2 runs after t1 finishes
g.add_tasks([t3, t4])                       # added task t3, t4
g.add_dependency(t3, waiting_for=[t1, t2])  # declare t3 to run after t1 & t2 finish
```

当任务的依赖关系图 `TaskGraph` 中有循环依赖的时候, `run` 会抛出一个`ValueError`，也可以直接调用 `has_cycle` 来检查:

```python
> g = TaskGraph()
> g.add_tasks([t1, t2])
> g.add_dependency(t1, waiting_for=t2)
> g.add_dependency(t2, waiting_for=t1)
> g.has_cycle()
[t1, t2, t1]
```

## Run Options

`TaskGraph.run` 也提供一些选项来自定义部分行为:

```python
g.run(
  title='Demo',           # Text shown at the left bottom corner
  callback=None,          # A function called when execution fail or succeed
  log_formatter=None,     # An instance of logging.Formatter, to specify the log format
  exit_on_success=False   # whether exit tui when execution succeed
)
```

`callback` 参数可以用来通知执行的结果，在执行结束的时候这个函数会被调用，一个布尔值会被传入来表示是否执行成功。`gtui.callback` 里提供一些简单的通知方法:

```python
# emit a desktop notification, use osascript on mac and notify-send on linux
from gtui import callback
g.run(callback.desktop_nofity(title='Plz See Here!', success_msg='Success', fail_msg='Fail'))
```

## Possible Problem with Stdout

向标准输出写内容会破坏命令行界面的展示。 `gtui` 把任务放在单独的线程里跑并且替换了 `sys.stdout` 所以大部分方法如 `print` 不需要改动就可以正常工作. 当在一个任务需要创建新线程的时候, 可以使用 `gtui.IORedirectedThread` 来达到相同的效果:

```python
from gtui import IORedirectedThread

t = IORedirectedThread(target=print, args=['hello world'])
t.start()
t.join()

content = t.get_stdout_content()
```

`gtui` 并没有对其他情况做处理，需要用户自己对这些情况做处理。
