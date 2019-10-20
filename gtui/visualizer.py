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
from additional_urwid_widgets.widgets.indicative_listbox import IndicativeListBox

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

    def __init__(self, widget: urwid.Text, log_formatter=default_log_formatter):
        self.widget = widget
        self.selected = False
        self.focus_on_log = False
        self.spinner_index = 0
        self.log_formatter = log_formatter

    def toggle_focus(self):
        self.focus_on_log = not self.focus_on_log

    def update_display(self):
        txt = '{selected}{status} {name}'.format(
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
    def text(self):
        return self.log_output if self.focus_on_log else self.output

    @property
    def log_output(self):
        return'\n'.join([self.log_formatter.format(r) for r in self.records])

    @property
    def output(self):
        """str : output of the sidebar task"""

    @property
    def name(self):
        """str : display name of the sidebar item"""

    @property
    def status(self):
        """str : one of the enums defined in TaskStatus"""

    @property
    def records(self):
        """Return a list of log records"""


class TaskTab(Tab):

    def __init__(self, task, executor, log_formatter):
        super().__init__(urwid.Text(''), log_formatter)
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

    @property
    def records(self):
        return self.executor.get_task_log_records(self.task)


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
        self.callback = callback
        self.exit_on_success = exit_on_success
        self.need_exit = False
        self.executor = Executor(graph, callback=self.wrapped_callback)

        self.tabs = [TaskTab(t, self.executor, log_formatter) for t in graph.tasks]
        self.selected_index = 0
        self.tabs[0].selected = True
        self.min_index = 0
        self.max_index = len(self.tabs) - 1

        #################
        # Urwid Widgets #
        #################

        # Main Display
        self.txt = urwid.Text('')
        self.scroll = urwid_scroll.Scrollable(self.txt)
        self.scroll_bar = urwid_scroll.ScrollBar(self.scroll)
        self.main_display = urwid.LineBox(self.scroll_bar, title='Output', title_align='left')
        self.should_follow_txt = True

        self.scroll_bar._command_map['h'] = urwid.CURSOR_PAGE_UP
        self.scroll_bar._command_map['l'] = urwid.CURSOR_PAGE_DOWN

        # Footer
        self.title = title
        self.txt_footer = urwid.Text('')
        self.footer = urwid.AttrMap(self.txt_footer, self.P_FOOTER)

        # SideBar
        self.sidebar_items = [tab.widget for tab in self.tabs]
        self.tab_box = IndicativeListBox(self.sidebar_items)
        self.sidebar = urwid.LineBox(self.tab_box, title='Task', title_align='left')

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
        if key == 'j':
            self.set_selected_tab(min(self.max_index, self.selected_index + 1))
            self.refresh_main_display()
            self.refresh_tab_display()

        if key == 'k':
            self.set_selected_tab(max(self.min_index, self.selected_index - 1))
            self.refresh_main_display()
            self.refresh_tab_display()

        if key == 'tab':
            self.get_selected_tab().toggle_focus()
            self.refresh_main_display()

        if key == 'q':
            raise urwid.ExitMainLoop()

        if key == 'y':
            output = self.get_selected_tab().text
            pyperclip.copy(output)

        if key == 't':
            logger.debug('%s : Toggle Text Follow Mode', key)
            self.should_follow_txt = not self.should_follow_txt
            self.refresh_footer_display()

        if key in ['h', 'l', 'up', 'down']:
            logger.debug('%s : Toggle Text Follow Mode', key)
            self.should_follow_txt = False
            self.refresh_footer_display()

    def get_selected_tab(self):
        return self.tabs[self.selected_index]

    def set_selected_tab(self, index):
        self.tabs[self.selected_index].selected = False
        self.selected_index = index
        self.tabs[self.selected_index].selected = True
        self.tab_box.select_item(self.selected_index)

    def refresh_main_display(self):
        sb_display = self.tabs[self.selected_index]
        self.txt.set_text(sb_display.text)

        if sb_display.focus_on_log:
            self.main_display.set_title('  Output | * Log')
        else:
            self.main_display.set_title('* Output |   Log')

        if self.should_follow_txt:
            self.scroll.set_scrollpos(-1)

    def refresh_tab_display(self):
        for tab in self.tabs:
            tab.update_display()

    def refresh_footer_display(self):
        text_content = [
            (self.P_TITLE, self.title),
            ' ',
            (self.P_KEY, 't'),
            ': tail -f {}'.format('[on] ' if self.should_follow_txt else '[off]'),
            ' ',
            (self.P_KEY, "tab"), ": switch output/log ",
            (self.P_KEY, "j/k"), ": switch task ",
            (self.P_KEY, "h/l/↑/↓"), ": scroll text ",
            (self.P_KEY, "y"), ": copy text ",
            (self.P_KEY, "q"), ": exits",
        ]
        self.txt_footer.set_text(text_content)

    def refresh_ui(self):
        self.refresh_tab_display()
        self.refresh_main_display()
        self.refresh_footer_display()

    def refresh_ui_every_half_second(self, loop=None, data=None):
        self.refresh_ui()

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
        self.refresh_footer_display()
        self.refresh_ui_every_half_second()
        self.loop.run()
