class EventEmitter:
    def __init__(self):
        self.listener = {}

    def emit(self, *args):
        for listener in self.listener.values():
            listener(*args)

    def subscribe(self, key, callback):
        self.listener[key] = callback

    def remove_subscription(self, key):
        del self.listener[key]
