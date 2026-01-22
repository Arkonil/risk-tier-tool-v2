from risc_tool.data.models.singleton import Singleton, SingletonMeta


def test_singleton_meta():
    class TestClass(metaclass=SingletonMeta):
        def __init__(self):
            self.value = 1

    instance1 = TestClass()
    instance2 = TestClass()

    assert instance1 is instance2
    assert instance1.value == 1

    instance1.value = 2
    assert instance2.value == 2


def test_singleton_inheritance():
    class MySingleton(Singleton):
        pass

    instance1 = MySingleton()
    instance2 = MySingleton()

    assert instance1 is instance2
