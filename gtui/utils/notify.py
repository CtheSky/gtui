import os
import platform

IS_RUNNING_ON_OSX = bool(platform.system() == 'Darwin')

def send(title, content):
    if IS_RUNNING_ON_OSX:
        os.system('osascript -e \'display notification "{}" with title "{}"\''.format(content, title))
    else:
        os.system('notify-send "{}" "{}"'.format(title, content))
