class Session:
    def __init__(self, debug_mode: bool = False):
        self.reset()

        self.debug_mode = debug_mode

    def reset(self):
        pass


__all__ = ["Session"]
