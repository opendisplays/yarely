def singleton(cls):
    """Provide a decorator for the singleton pattern."""
    instances = {}

    def getinstance(*args, **kwargs):
        """Return the singleton instance.
        Note that args and kwargs are only used on the first call for each
        class.
        Example:
            >>> from yarely.core.helpers import singleton
            >>> @singleton
            ... class Test:
            ...     def __init__(self, flag=False):
            ...         self.flag = flag
            ...
            >>> a = Test()
            >>> b = Test(True)
            >>> a.flag
            False
            >>> b.flag
            False
        """
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return getinstance
