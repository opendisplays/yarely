def log_exception(log, message=None):
    """Provide a decorator that logs exceptions before rethrowing them.
    Parameter log should be a logging.Logger instance to which exceptions
    will be recorded, prefixed with the optional message.
    Useful for methods calling into a host library (eg PyObjC) which tend
    to forget the stack.
    """

    if message is None:
        message = "Exception:"

    def decorator(func):
        def wrapper(*args, **kwargs):
            try:
                return func(*args, **kwargs)
            except:
                log.exception(message)
                raise
        return wrapper
    return decorator
