"""
A Visualizer to display the Text User Interface.

It's based on the awesome lib urwid. It uses the
executor implemented in gtui.executor to execute
the tasks and track the output & logs of each task.
"""
import string
import logging

import urwid
import pyperclip

from .task import Task, TaskStatus, TaskGraph
from .executor import Executor
from .utils import urwid_scroll
from .utils import default_log_formatter

logger = logging.getLogger(__name__)


class Tab:
    """
    An UI element to be displayed on the sidebar.
    It controls how the sidbar item is rendered and
    track the output associated with this tab.
    """

    UNICODE_CROSS = '\U00002717'
    UNICODE_CHECK_MARK = '\U00002713'
    UNICODE_SPINNER_LIST = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    def __init__(self, index, widget: urwid.Text):
        self.index = index
        self.widget = widget
        self.selected = False
        self.spinner_index = 0

    def update_display(self):
        txt = '{index}{selected}| {status} {name}'.format(
            index=self.index,
            selected='*' if self.selected else ' ',
            status=self.tab_status_str,
            name=self.name
        )
        self.widget.set_text(txt)

    @property
    def tab_status_str(self):
        """str : represents the current task status"""
        if self.status == TaskStatus.Success:
            return self.UNICODE_CHECK_MARK
        if self.status == TaskStatus.Failure:
            return self.UNICODE_CROSS
        if self.status == TaskStatus.Running:
            self.spinner_index = (self.spinner_index + 1) % len(self.UNICODE_SPINNER_LIST)
            return self.UNICODE_SPINNER_LIST[self.spinner_index]
        return ' '

    @property
    def name(self):
        """str : display name of the sidebar item"""

    @property
    def status(self):
        """str : one of the enums defined in TaskStatus"""

    @property
    def output(self):
        """str : output of the sidebar task"""

class TabForTaskOutput(Tab):
    """Tab to display task output"""

    def __init__(self, index, task, executor):
        super().__init__(index, urwid.Text(''))
        self.task: Task = task
        self.executor: Executor = executor
        self.update_display()

    @property
    def name(self):
        return self.task.name

    @property
    def status(self):
        return self.executor.get_task_status(self.task)

    @property
    def output(self):
        return self.executor.get_task_output(self.task)

class TabForLog(Tab):
    """Tab to display logs"""

    def __init__(self, index, widget: urwid.Text, log_formatter: logging.Formatter):
        super().__init__(index, widget)
        self.log_formatter = log_formatter

    @property
    def records(self):
        """Return a list of log records"""

    @property
    def output(self):
        output = '\n'.join([self.log_formatter.format(r) for r in self.records])
        return output

class TabForTaskLog(TabForLog):
    """Tab to display task logs"""

    def __init__(self, index, task, executor, log_formatter):
        super().__init__(index, urwid.Text(''), log_formatter)
        self.task: Task = task
        self.executor: Executor = executor
        self.update_display()

    @property
    def name(self):
        return self.task.name

    @property
    def status(self):
        return self.executor.get_task_status(self.task)

    @property
    def records(self):
        return self.executor.get_task_log_records(self.task)


class TabForMainThreadLog(TabForLog):
    """Tab to display TUI main event loop logs"""

    def __init__(self, index, executor, log_formatter):
        super().__init__(index, urwid.Text(''), log_formatter)
        self.executor: Executor = executor
        self.update_display()

    @property
    def name(self):
        return 'Main Event Loop'

    @property
    def status(self):
        return TaskStatus.Running

    @property
    def records(self):
        return self.executor.get_main_thread_log_records()


class Visualizer:

    P_KEY      = 'key'
    P_TITLE    = 'title'
    P_FOOTER   = 'footer'
    P_SELECTED = 'selected'

    PALETTE = [
        (P_KEY, 'light cyan', 'black'),
        (P_TITLE, 'white', 'black'),
        (P_FOOTER, 'light gray', 'black'),
        (P_SELECTED, 'underline', ''),
    ]

    FOOTER_INSTRUCTION_CONTENT = [
        (P_KEY, "UP"), ", ", (P_KEY, "DOWN"), " : scroll text ",
        (P_KEY, "NUMBER"), " : select tab ",
        (P_KEY, "Q"), " : exits",
    ]

    TAB_INDEX = list(string.digits)[1:] + list(string.ascii_lowercase)

    def __init__(self, graph: TaskGraph, log_formatter, title, callback=None, exit_on_success=False):
        """Init a visualizer with the task graph and other options.

        Parameters
        ----------
        title : str
            The title of TUI, will be displayed at left bottom corner.
        callback : functoin
            A function which accepts a boolean indicating whether execution succeeds.
            It will be called when execution finishes.
        log_formatter: logging.Formatter
            An instance of logging.Formatter. Defaults to gtui.utils.default_log_formatter.
        exit_on_success: boolean
            Whether exit TUI if all tasks succeed. Defaults to False.
        """
        self.graph = graph
        self.tasks = graph.tasks
        self.callback = callback
        self.exit_on_success = exit_on_success
        self.need_exit = False
        self.executor = Executor(graph, callback=self.wrapped_callback)

        self.selected_index = None
        self.index2tab = {}
        self.index2task_tab = {}
        self.index2debug_tab = {}
        for i, task in enumerate(self.tasks):
            index = self.TAB_INDEX[i]
            tab = TabForTaskOutput(index, task, self.executor)
            self.index2tab[index] = tab
            self.index2task_tab[index] = tab

        main_debug_tab_index = self.TAB_INDEX[len(self.tasks)]
        main_debug_tab = TabForMainThreadLog(main_debug_tab_index, self.executor, log_formatter)
        self.index2tab[main_debug_tab_index] = main_debug_tab
        self.index2debug_tab[main_debug_tab_index] = main_debug_tab

        for i, task in enumerate(self.tasks):
            index = self.TAB_INDEX[i + len(self.tasks) + 1]
            tab = TabForTaskLog(index, task, self.executor, log_formatter)
            self.index2tab[index] = tab
            self.index2debug_tab[index] = tab

        #################
        # Urwid Widgets #
        #################

        # Main Display
        self.txt = urwid.Text('')
        self.scroll = urwid_scroll.Scrollable(self.txt)
        self.scroll_bar = urwid_scroll.ScrollBar(self.scroll)
        self.main_display = urwid.LineBox(self.scroll_bar)
        self.should_follow_txt = True

        # Footer
        self.title = title
        self.txt_footer = urwid.Text('')
        self.footer = urwid.AttrMap(self.txt_footer, self.P_FOOTER)

        # SideBar
        self.sidebar_items = [
            urwid.Divider('='),
            urwid.Text('Task'),
            urwid.Divider('=')
        ] + [
            self.index2task_tab[i].widget
            for i in sorted(self.index2task_tab.keys())
        ] + [
            urwid.Divider('='),
            urwid.Text('Debug Info'),
            urwid.Divider('=')
        ] + [
            self.index2debug_tab[i].widget
            for i in sorted(self.index2debug_tab.keys())
        ]
        self.sidebar = urwid.ListBox(self.sidebar_items)

        # Topmost Frame
        self.columns = urwid.Columns(
            [(35, self.sidebar), self.main_display],
            dividechars=2,
            focus_column=1
        )
        self.frame = urwid.Frame(
            body=self.columns,
            footer=self.footer
        )

        # Main Event Loop & Task Executor
        self.loop = urwid.MainLoop(
            self.frame,
            self.PALETTE,
            unhandled_input=self.handle_input,
            handle_mouse=False
        )

    def handle_input(self, key):
        if key in self.index2tab:
            logger.debug('%s : Switch to tab %s', key, key)
            self.set_selected_tab(key)
            self.refresh_tab_display()
            self.refresh_main_display()

        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

        if key in ('y', 'Y'):
            output = self.get_selected_tab().output
            pyperclip.copy(output)

        if key == 'f3':
            logger.debug('%s : Toggle Text Follow Mode', key)
            self.should_follow_txt = not self.should_follow_txt
            self.refresh_footer_display()

        if key in ['up', 'down', 'home', 'end', 'page up', 'page down']:
            logger.debug('%s : Toggle Text Follow Mode', key)
            self.should_follow_txt = False
            self.refresh_footer_display()

    def get_selected_tab(self):
        return self.index2tab[self.selected_index]

    def set_selected_tab(self, index):
        self.selected_index = index
        for i, tab in self.index2tab.items():
            tab.selected = bool(i == index)

    def refresh_main_display(self):
        sb_display = self.index2tab[self.selected_index]
        output = sb_display.output
        self.txt.set_text(output)

        if self.should_follow_txt:
            self.scroll.set_scrollpos(-1)

    def refresh_tab_display(self):
        for tab in self.index2tab.values():
            tab.update_display()

    def refresh_footer_display(self):
        text_content = [
            (self.P_TITLE, self.title),
            ' ',
            (self.P_KEY, 'F3'),
            ': toggle tail -f mode {}'.format('[on] ' if self.should_follow_txt else '[off]'),
            ' ',
            (self.P_KEY, "UP"), ", ", (self.P_KEY, "DOWN"), ": scroll text ",
            (self.P_KEY, "NUMBER"), ": select tab ",
            (self.P_KEY, "Y"), ": copy text ",
            (self.P_KEY, "Q"), ": exits",
        ]
        self.txt_footer.set_text(text_content)

    def refresh_ui_every_half_second(self, loop=None, data=None):
        self.refresh_main_display()
        self.refresh_tab_display()

        if self.need_exit:
            raise urwid.ExitMainLoop()

        self.loop.set_alarm_in(0.5, self.refresh_ui_every_half_second)

    def wrapped_callback(self, is_success):
        if self.callback:
            self.callback(is_success)

        if is_success and self.exit_on_success:
            self.need_exit = True

    def run(self):
        self.executor.start_execution()
        self.set_selected_tab('1')
        self.refresh_footer_display()
        self.refresh_ui_every_half_second()
        self.loop.run()
