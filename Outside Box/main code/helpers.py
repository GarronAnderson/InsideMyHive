import digitalio
import time


class RunningAverage:
    def __init__(self, avg=0, nvalues=0):
        self._avg = avg
        self._nvalues = nvalues

    def __str__(self):
        return str(self.avg)

    def __repr__(self):
        return f"RunningAverage(avg={self._avg}, nvalues={self._nvalues})"

    def update(self, value):
        self._avg = self._avg + ((value - self._avg) / (self._nvalues + 1))
        self._nvalues = self._nvalues + 1

    @property
    def avg(self):
        return self._avg

    def reset(self, avg=0):
        self._avg = avg
        self._nvalues = 0


class StatusLED:
    def __init__(self, pin, active_low=True):
        self._pin = pin
        self._active_low = active_low

        self._io = digitalio.DigitalInOut(pin)
        self._io.direction = digitalio.Direction.OUTPUT
        self._io.value = int(active_low)

    def __str__(self):
        return f"Status LED Pin {self._pin}"

    def __repr__(self):
        return f"StatusLED({self._pin}, active_low={self_active_low})"

    def on(self):
        self._io.value = int(not self._active_low)

    def off(self):
        self._io.value = int(self._active_low)

    def toggle(self):
        self._io.value = 1 - self._io.value

    def blink(self, num, delay=0.5, initial_delay=0.5):
        self.off()
        time.sleep(initial_delay)
        for _ in range(num):
            self.on()
            time.sleep(delay)
            self.off()
            time.sleep(delay)
