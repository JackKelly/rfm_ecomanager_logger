class Sensor(object):
    """Each Transmitter can have 1 to 3 Sensors."""
    def __init__(self, name=None, log_chan=None):
        self.name = name
        self.log_chan = log_chan


class Transmitter(object):
    def __init__(self, sensors={}):
        self.sensors = sensors
