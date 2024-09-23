from . import get

class Kabutan():
    def __init__(self, log):
        self.get = get.Get(log)