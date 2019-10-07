import logging

default_log_formatter = logging.Formatter(
    fmt='[%(asctime)-15s][%(name)s][%(message)s]',
    datefmt='%Y-%m-%d %H:%M:%S'
)
