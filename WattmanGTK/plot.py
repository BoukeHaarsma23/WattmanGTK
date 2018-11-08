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

from matplotlib.figure import Figure        # required for plot
from matplotlib.ticker import AutoLocator
from matplotlib.backends.backend_gtk3cairo import FigureCanvasGTK3Cairo as FigureCanvas # required for GTK3 integration
import numpy as np  # required for matplotlib data types
import gi                   # required for GTK3
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk, Gdk
from WattmanGTK.plotsignal import Plotsignal

def convert_to_si(unit, value=0):
    # First char in unit should have prefix
    # https://en.wikipedia.org/wiki/Metric_prefix
    if 'µ' == unit[1]:
        return unit[0] + unit[2:], value / 1000000
    elif 'm' == unit[1]:
        return unit[0] + unit[2:], value / 1000
    elif 'c' == unit[1]:
        return unit[0] + unit[2:], value / 100
    elif 'd' == unit[1]:
        return unit[0] + unit[2:], value / 10
    elif 'k' == unit[1]:
        return unit[0] + unit[2:], value * 1000
    elif 'M' == unit[1]:
        if 'MHz' in unit:
            # exception for MHz, just return value here
            return unit, value
        return unit[0] + unit[2:], value * 1000000
    elif 'G' == unit[1]:
        if 'GHz' in unit:
            # exception for GHz, just return value here
            return unit, value
        return unit[0] + unit[2:], value * 1000000000
    # no conversion available/ no prefix --> return original
    return unit, value

class Plot:
    # TODO scaling of size when resizing
    # TODO tighter fit of plot
    # TODO BUG: weird redrawing issue on changing panes, probably should not redraw graph on changing panes
    # Plot object used GUI
    def __init__(self,builder,GPU,maxpoints,precision,linux_kernelmain,linux_kernelsub):
        # Can used for kernel specific workarounds
        self.linux_kernelmain = linux_kernelmain
        self.linux_kernelsub = linux_kernelsub

        self.precision = precision
        self.builder = builder
        self.GPU = GPU
        self.maxpoints = maxpoints
        self.fig = Figure(figsize=(1000, 150), dpi=100, facecolor="#00000000")
        self.fig.set_tight_layout(True)
        self.ax = self.fig.add_subplot(111)
        # enable, name, unit, mean, max, current
        self.signalstore = Gtk.ListStore(bool, bool, str, str, str, str, str, str)
        self.Plotsignals = self.init_signals(self.GPU)
        self.init_treeview()
        self.update_signals()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.set_size_request(1000, 150)
        self.object = self.builder.get_object("matplot")
        self.object.add(self.canvas)
        self.object.show_all()


    def init_signals(self,GPU):
        Plotsignals = []

        # Define signals with: names units max min path plotenable plotnormalise plotcolor parser and outputargument used from parser
        Plotsignals.append(Plotsignal("GPU Clock", "[MHz]", GPU.pstate_clock[-1], GPU.pstate_clock[0],
                                      "/pp_dpm_sclk", True, True, "#1f77b4",GPU.get_current_clock,0))
        Plotsignals.append(Plotsignal("GPU State", "[-]", len(GPU.pstate_clock)-1, 0,
                                      "/pp_dpm_sclk", True, True, "#ff7f0e",GPU.get_current_clock,1))
        Plotsignals.append(Plotsignal("MEM Clock", "[MHz]", GPU.pmem_clock[-1], GPU.pmem_clock[0],
                                      "/pp_dpm_mclk", True, True, "#d62728",GPU.get_current_clock,0))
        Plotsignals.append(Plotsignal("MEM State", "[-]", len(GPU.pmem_clock)-1, 0,
                                      "/pp_dpm_mclk", True, True, "#9467bd",GPU.get_current_clock,1))
        if GPU.fanpwmsensors is not None:
            Plotsignals.append(Plotsignal("FAN Speed", "[0-255]", GPU.fanpwmsensors.read_attribute('_max',True), 0,
                                      GPU.fanpwmsensors.path, True, True, "#8c564b",GPU.fanpwmsensors.read))
        if GPU.tempsensors is not None:
            Plotsignals.append(Plotsignal("TEMP 1", "[m°C]", GPU.tempsensors.read_attribute('_crit',True), 0,
                                      GPU.tempsensors.path, True, True, "#e377c2",GPU.tempsensors.read))
        if GPU.powersensors is not None:
            Plotsignals.append(Plotsignal("POWER", "[µW]", GPU.powersensors.read_attribute('_cap',True), 0,
                                      GPU.powersensors.path, True, True, "#7f7f7f", GPU.powersensors.read))


        # GPU busy percent only properly available in linux version 4.19+
        if (self.linux_kernelmain == 4 and self.linux_kernelsub > 18) or (self.linux_kernelmain >= 5):
            Plotsignals.append(Plotsignal("GPU Usage", "[-]", 100, 0, "/gpu_busy_percent", True, True, "#2ca02c", parser=GPU.read_sensor))

        return Plotsignals

    def init_treeview(self):
        textrenderer = Gtk.CellRendererText()
        plotrenderer = Gtk.CellRendererToggle()
        plotrenderer.connect("toggled", self.on_plot_toggled)
        normaliserenderer = Gtk.CellRendererToggle()
        normaliserenderer.connect("toggled", self.on_normalise_toggled)
        self.tree = self.builder.get_object("Signal Selection")
        self.tree.append_column(Gtk.TreeViewColumn("Plot", plotrenderer, active=0))
        self.tree.append_column(Gtk.TreeViewColumn("Scale", normaliserenderer, active=1))
        columnnames=["Name","Unit","mean","max","current"]
        for i,column in enumerate(columnnames):
            tcolumn = Gtk.TreeViewColumn(column,textrenderer,text=i+2,foreground=7)
            self.tree.append_column(tcolumn)

        for plotsignal in self.Plotsignals:
            self.signalstore.append([plotsignal.plotenable, plotsignal.plotnormalise, plotsignal.name, convert_to_si(plotsignal.unit)[0], '0', '0', '0', plotsignal.plotcolor])
        self.tree.set_model(self.signalstore)

    def update_signals(self):
        # Retrieve signal and set appropriate values in signalstore to update left pane in GUI
        for i,Plotsignal in enumerate(self.Plotsignals):
            Plotsignal.retrieve_data(self.maxpoints)
            self.signalstore[i][4]=str(np.around(convert_to_si(Plotsignal.unit,Plotsignal.get_mean())[1],self.precision))
            self.signalstore[i][5]=str(np.around(convert_to_si(Plotsignal.unit,Plotsignal.get_max())[1],self.precision))
            self.signalstore[i][6]=str(np.around(convert_to_si(Plotsignal.unit,Plotsignal.get_last_value())[1],self.precision))


    def on_plot_toggled(self, widget, path):
        self.signalstore[path][0] = not self.signalstore[path][0]
        self.Plotsignals[int(path)].plotenable = not self.Plotsignals[int(path)].plotenable
        self.update_plot()

    def on_normalise_toggled(self, widget, path):
        self.signalstore[path][1] = not self.signalstore[path][1]
        self.Plotsignals[int(path)].plotnormalise = not self.Plotsignals[int(path)].plotnormalise
        self.update_plot()

    def update_plot(self):
        self.ax.clear()
        for Plotsignal in self.Plotsignals:
            if Plotsignal.plotenable:
                if Plotsignal.plotnormalise:
                    data = Plotsignal.get_normalised_values()
                    self.ax.plot(data, color=Plotsignal.plotcolor)
                else:
                    data = Plotsignal.get_values()
                    self.ax.plot(convert_to_si(Plotsignal.unit,data)[1], color=Plotsignal.plotcolor)


        self.ax.grid(True)
        self.ax.get_yaxis().tick_right()
        self.ax.get_yaxis().set_visible(True)
        self.ax.get_xaxis().set_visible(False)
        all_normalised = True
        iter = self.signalstore.get_iter(0)
        while iter is not None:
            if self.signalstore[iter][1] == False:
                all_normalised = False
                break
            iter = self.signalstore.iter_next(iter)
        if all_normalised:
            self.ax.set_yticks(np.arange(0, 1.1, step=0.1))
        else:
            self.ax.yaxis.set_major_locator(AutoLocator())
        self.canvas.draw()
        self.canvas.flush_events()

    def refresh(self):
        # This is run in thread
        self.update_signals()
        self.update_plot()
