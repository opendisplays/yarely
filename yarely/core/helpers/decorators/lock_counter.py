import time
import logging


log = logging.getLogger(__name__)


def semaphore_lock_decorator(f):
    """ Semaphore lock decorator counts the number of times the method was
    called (using the class variable semaphore_lock_decorator_flag). If the
    method was called more than once, we will wait and call the method again
    once it is finished. Only at most one request at a time can be waiting for
    the method - this will prevent the method to be called over and over again.
    """
    def wrapper(*args, **kwargs):

        # Increase as a new request came in.
        args[0].semaphore_lock_decorator_flag += 1

        # If we are already waiting for the method, stop here.
        if args[0].semaphore_lock_decorator_flag > 2:
            log.debug("LOCK is {}, stopping ... ".format(
                args[0].semaphore_lock_decorator_flag
            ))
            args[0].semaphore_lock_decorator_flag -= 1
            return

        # Wait as long as the method has not finished.
        while args[0].semaphore_lock_decorator_flag > 1:
            log.debug("LOCK is {}, waiting... ".format(
                args[0].semaphore_lock_decorator_flag
            ))
            time.sleep(0.1)

        # Start the actual method and decrease the flag once it's finished.
        f(*args, **kwargs)
        args[0].semaphore_lock_decorator_flag -= 1

    return wrapper
