import asyncio
import sys

class Server(object):
    TICK_RATE = 10
    
    def __init__(self, loop, universe):
        self.loop = loop
        self.tick_rate = self.TICK_RATE
        self.tick_time = 1/float(self.tick_rate)
        self.universe = universe
        self.stopping = False
        self.finished = asyncio.Future()

    def start(self):
        self.schedule_tick()

    def stop(self):
        self.stopping = True

    def wait_finished(self):
        return self.finished

    def schedule_tick(self, when=None):
        if when == None:
            when = self.loop.time() + self.tick_time
        self.loop.call_at(when, self.tick)

    def tick(self):
        try:
            self.universe.tick()
        except:
            sys.excepthook(*sys.exc_info())

        if not self.stopping:
            self.schedule_tick()
        else:
            self.finished.set_result(None)
