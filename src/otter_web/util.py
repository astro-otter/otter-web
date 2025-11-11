class _TimeoutError(Exception):
    pass

def _timeout_handler(signum, frame):
    raise _TimeoutError("Function has timed out!")
