"""
Module Providing Base Singleton class
"""


class SingletonMeta(type):
    """
    A metaclass that creates a Singleton base class.
    Any class inheriting from this base class will be a singleton.
    """

    _instances = {}

    def __call__(cls, *args, **kwargs):
        """
        Ensures that only one instance of the class exists.
        If an instance already exists, it is returned.
        """
        if cls not in cls._instances:
            cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]


class Singleton(metaclass=SingletonMeta):
    """
    Base class for singleton classes.
    """

    def __init__(self):
        pass
