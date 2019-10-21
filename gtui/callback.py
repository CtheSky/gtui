"""Some common callbacks to be registered on graph execution"""
import os
import platform

_IS_RUNNING_ON_OSX = platform.system() == 'Darwin'

def _send_desktop_notify(title, content):
    if _IS_RUNNING_ON_OSX:
        os.system('osascript -e \'display notification "{}" with title "{}"\''.format(content, title))
    else:
        os.system('notify-send "{}" "{}"'.format(title, content))

def desktop_notify(title, success_msg, fail_msg):
    """Returns a callback which emits a desktop notification according to execution result."""
    def callback(is_success):
        _send_desktop_notify(title=title, content=success_msg if is_success else fail_msg)
    return callback
