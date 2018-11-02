import numpy as np


class Plotsignal:
    def __init__(self, name, unit, max=1, min=0, sensorpath='', plotenable=False, plotcolor='#000000', parser=None, outputnr=None):
        self.name = name
        self.unit = unit
        self.sensorpath = sensorpath
        self.plotenable = plotenable
        self.plotcolor = plotcolor
        self.max = max
        self.min = min
        self.parser = parser
        self.outputnr = outputnr
        self.data = None

    def retrieve_data(self,maxpoints):
        if self.parser is None:
            print("No parser for " + self.name + "cannot retrieve signal")
            return
        else:
            if self.outputnr is None:
                self.add_value(self.parser(self.sensorpath),maxpoints)
            else:
                self.add_value(self.parser(self.sensorpath)[self.outputnr],maxpoints)

    def get_max(self):
        return np.max(self.get_values())

    def get_mean(self):
        return np.mean(self.get_values())

    def add_value(self,value,maxpoints):
        if self.data is None:
            self.data = np.array([value])
            return
        if len(self.data) < maxpoints:
            self.data = np.append(self.data,value)
        else:
            self.data = np.append(self.data[-maxpoints:],value)

    def get_values(self):
        if self.data is not None:
            return self.data
        return None

    def get_last_value(self):
        if self.data is not None:
            if len(self.data) > 1:
                return self.data[-1]
            return self.data[0]
        return None

    def get_normalised_values(self):
        if self.get_values():
            return (self.get_values() - self.min) / (self.max - self.min)
        return None

    def convert(self,value):
        # TODO
        # could be used to convert between SI and for the Freedom people which use Fahrenheit
        return


