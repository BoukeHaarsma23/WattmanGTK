# This file is part of WattmanGTK.
#
# Copyright (c) 2018 Bouke Haarsma
#
# WattmanGTK is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.
# 
#
# WattmanGTK is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with WattmanGTK.  If not, see <http://www.gnu.org/licenses/>.

import numpy as np


class Plotsignal:
    def __init__(self, name, unit, max=1, min=0, sensorpath='', plotenable=False, plotnormalise=False, plotcolor='#000000', parser=None, outputnr=None):
        self.name = name
        self.unit = unit
        self.sensorpath = sensorpath
        self.plotenable = plotenable
        self.plotnormalise = plotnormalise
        self.plotcolor = plotcolor
        self.max = max
        self.min = min
        self.parser = parser
        self.outputnr = outputnr
        self.data = None

    def retrieve_data(self,maxpoints):
        if self.parser is None:
            print(f"No parser for {self.name} cannot retrieve signal")
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

    def get_min(self):
        return np.min(self.get_values())

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

    def all_equal(self):
        return all(self.data[1:] == self.data[:-1])

    def get_normalised_values(self):
        if self.data is not None:
            if (self.max - self.min) != 0:
                return (self.get_values() - self.min) / (self.max - self.min)
            else:
                # cannot divide by zero, returning scaled values by currents
                with np.errstate(divide='raise',invalid='raise'):
                    try:
                        return (self.get_values() - self.get_min()) / (self.get_max() - self.get_min())
                    except FloatingPointError:
                        # cannot divide 0 by 0, return 0
                        return self.get_values() * 0
        return None
