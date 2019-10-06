import time
import urwid
import string
import logging
import pyperclip

from .task import Task, TaskStatus, TaskGraph
from .executor import Executor
from .utils import notify
from .utils import urwid_scroll

logger = logging.getLogger(__name__)


class TabWithDisplay:
    """抽象了对应一个输出的 Sidebar Tab 标签，子类实现不同的获取输出的逻辑, widget 为对应在 Sidebar 中的 Text Widget"""

    UNICODE_CROSS = '\U00002717'
    UNICODE_CHECK_MARK = '\U00002713'
    UNICODE_SPINNER_LIST = ["⣾", "⣽", "⣻", "⢿", "⡿", "⣟", "⣯", "⣷"]

    def __init__(self, index, widget: urwid.Text):
        self.index = index
        self.widget = widget
        self.selected = False

    def update_display(self):
        txt = '{index}{selected}| {status} {name}'.format(
            index=self.index,
            selected='*' if self.selected else ' ',
            status=self.status,
            name=self.name
        )
        self.widget.set_text(txt)

    @property
    def name(self):
        """str : display name of the sidebar item"""

    @property
    def status(self):
        """str : status of the sidebar task"""

    @property
    def output(self):
        """str : output of the sidebar task"""

class TabWithTaskOutput(TabWithDisplay):

    def __init__(self, index, task, executor):
        super().__init__(index, urwid.Text(''))
        self.task: Task = task
        self.executor: Executor = executor
        self.spinner_index = 0
        self.update_display()

    @property
    def name(self):
        return self.task.name

    @property
    def status(self):
        status = self.executor.get_task_status(self.task)
        if status == TaskStatus.Success:
            return self.UNICODE_CHECK_MARK
        if status == TaskStatus.Failure:
            return self.UNICODE_CROSS
        if status == TaskStatus.Running:
            self.spinner_index = (self.spinner_index + 1) % len(self.UNICODE_SPINNER_LIST)
            return self.UNICODE_SPINNER_LIST[self.spinner_index]
        return ' '

    @property
    def output(self):
        return self.executor.get_task_output(self.task)

class TabWithTaskLogInfo(TabWithDisplay):

    def __init__(self, index, task, executor):
        super().__init__(index, urwid.Text(''))
        self.task: Task = task
        self.executor: Executor = executor
        self.spinner_index = 0
        self.update_display()

    @property
    def name(self):
        return self.task.name

    @property
    def status(self):
        status = self.executor.get_task_status(self.task)
        if status == TaskStatus.Success:
            return self.UNICODE_CHECK_MARK
        if status == TaskStatus.Failure:
            return self.UNICODE_CROSS
        if status == TaskStatus.Running:
            self.spinner_index = (self.spinner_index + 1) % len(self.UNICODE_SPINNER_LIST)
            return self.UNICODE_SPINNER_LIST[self.spinner_index]
        return ' '

    @property
    def output(self):
        thread = self.executor.get_task_thread(self.task)
        records = self.executor.log_collector.get_thread_log_records(thread.name)
        output = '\n'.join([
            '[{}][{}][{}]'.format(
                time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r.created)),
                r.name,
                r.getMessage()
            ) for r in records
        ])
        return output

class TabWithMainTheadLogInfo(TabWithDisplay):

    def __init__(self, index, executor):
        super().__init__(index, urwid.Text(''))
        self.executor: Executor = executor
        self.spinner_index = 0
        self.update_display()

    @property
    def name(self):
        return 'Main Event Loop'

    @property
    def status(self):
        self.spinner_index = (self.spinner_index + 1) % len(self.UNICODE_SPINNER_LIST)
        return self.UNICODE_SPINNER_LIST[self.spinner_index]

    @property
    def output(self):
        records = self.executor.log_collector.get_main_thread_log_records()
        output = '\n'.join([
            '[{}][{}][{}]'.format(
                time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(r.created)),
                r.name,
                r.getMessage()
            ) for r in records
        ])
        return output


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

    def __init__(self, graph: TaskGraph, title='Demo', success_msg='Success', fail_msg='Failed'):
        self.tasks = graph.tasks
        self.success_msg = success_msg
        self.fail_msg = fail_msg
        self.executor = Executor(graph, callback=self.desktop_notify_result)

        self.selected_index = None
        self.index2tab = {}
        self.index2task_tab = {}
        self.index2debug_tab = {}
        for i, task in enumerate(self.tasks):
            index = self.TAB_INDEX[i]
            tab = TabWithTaskOutput(index, task, self.executor)
            self.index2tab[index] = tab
            self.index2task_tab[index] = tab

        main_debug_tab_index = self.TAB_INDEX[len(self.tasks)]
        main_debug_tab = TabWithMainTheadLogInfo(main_debug_tab_index, self.executor)
        self.index2tab[main_debug_tab_index] = main_debug_tab
        self.index2debug_tab[main_debug_tab_index] = main_debug_tab

        for i, task in enumerate(self.tasks):
            index = self.TAB_INDEX[i + len(self.tasks) + 1]
            tab = TabWithTaskLogInfo(index, task, self.executor)
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
        self.if_follow_txt = True

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
        if key in ('q', 'Q'):
            raise urwid.ExitMainLoop()

        if key in self.index2tab:
            logger.debug('Switch to tab : %s', key)
            self.set_selected_tab(key)
            self.refresh_tab_display()
            self.refresh_main_display()

        if key in ('y', 'Y'):
            output = self.get_selected_tab().output
            pyperclip.copy(output)

        if key == 'f3':
            logger.debug('Toggle Text Follow Mode')
            self.if_follow_txt = not self.if_follow_txt
            self.refresh_footer_display()

        if key in (urwid.CURSOR_UP, urwid.CURSOR_DOWN, urwid.CURSOR_PAGE_UP, urwid.CURSOR_PAGE_DOWN):
            self.if_follow_txt = False

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
        if self.if_follow_txt:
            self.scroll.set_scrollpos(-1)

    def refresh_main_display_every_second(self, loop=None, data=None):
        self.refresh_main_display()
        self.loop.set_alarm_in(1, self.refresh_main_display_every_second)

    def refresh_tab_display(self):
        for tab in self.index2tab.values():
            tab.update_display()

    def refresh_tab_display_every_half_second(self, loop=None, data=None):
        self.refresh_tab_display()
        self.loop.set_alarm_in(0.5, self.refresh_tab_display_every_half_second)

    def refresh_footer_display(self):
        text_content = [
            (self.P_TITLE, self.title),
            ' ',
            (self.P_KEY, 'F3'),
            ': toggle tail -f mode {}'.format('[on] ' if self.if_follow_txt else '[off]'),
            ' ',
            (self.P_KEY, "UP"), ", ", (self.P_KEY, "DOWN"), ": scroll text ",
            (self.P_KEY, "NUMBER"), ": select tab ",
            (self.P_KEY, "Y"), ": copy text ",
            (self.P_KEY, "Q"), ": exits",
        ]
        self.txt_footer.set_text(text_content)

    def desktop_notify_result(self, is_success):
        if is_success:
            notify.send(title='Gli Info', content=self.success_msg)
        else:
            notify.send(title='Gli Error', content=self.fail_msg)

    def run(self):
        self.executor.start_execution()
        self.set_selected_tab('1')
        self.refresh_footer_display()
        self.refresh_main_display_every_second()
        self.refresh_tab_display_every_half_second()
        self.loop.run()
