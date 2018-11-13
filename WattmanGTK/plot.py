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
from WattmanGTK.util import read, convert_to_si

subsystem_unit_color = \
    {"in": {"unit": "[mV]", "color": "#8c564b"},
     "fan": {"unit": "[RPM]", "color": "#e377c2"},
     "temp": {"unit": "[m°C]", "color": "#7f7f7f"},
     "power": {"unit": "[µW]", "color": "#bcbd22"},
     "pwm": {"unit":"[0-255]", "color": "#17becf"}}
sensors_to_plot = ["pwm", "input", "average"] #sensors to plot if string is subset, examples: temp1_input power1_average
disable_plots_if_scaling_error = False #True: Disable plots when scaling has errors False: keeps unnormalised plots


class Plot:
    # TODO scaling of size when resizing
    # TODO tighter fit of plot
    # TODO BUG: weird redrawing issue on changing panes, probably should not redraw graph on changing panes
    # Plot object used GUI
    def __init__(self,builder,GPUs,maxpoints,precision,linux_kernelmain,linux_kernelsub):
        # Can used for kernel specific workarounds
        self.linux_kernelmain = linux_kernelmain
        self.linux_kernelsub = linux_kernelsub

        self.precision = precision
        self.builder = builder
        self.GPUs = GPUs
        self.GPU = GPUs[0]
        self.maxpoints = maxpoints
        self.fig = Figure(figsize=(1000, 150), dpi=100, facecolor="#00000000")
        self.fig.set_tight_layout(True)
        self.ax = self.fig.add_subplot(111)
        # enable, name, unit, mean, max, current
        self.signalstore = Gtk.ListStore(bool, bool, bool, str, str, str, str, str, str, str)
        self.Plotsignals = self.init_signals(self.GPU)

        # Set top panel height in accordance to number of signals (with saturation)
        height_top_panel = len(self.Plotsignals)*32.5
        if height_top_panel < 150:
            self.builder.get_object("MainPane").set_position(150)
        elif height_top_panel > 235:
            self.builder.get_object("MainPane").set_position(235)
        else:
            self.builder.get_object("MainPane").set_position(height_top_panel)

        self.init_treeview()
        self.update_signals()
        self.canvas = FigureCanvas(self.fig)
        self.canvas.set_size_request(1000, 150)
        self.object = self.builder.get_object("matplot")
        self.object.add(self.canvas)
        self.object.show_all()

    def change_GPU(self,cardnr):
        print(f"Changing plot to GPU {self.GPUs[cardnr].fancyname}")
        self.GPU = self.GPUs[cardnr]
        self.Plotsignals = self.init_signals(self.GPU)
        self.init_treeview()
        self.update_signals()


    def init_signals(self,GPU):
        Plotsignals = []

        # Define signals with: names units max min path plotenable plotnormalise plotcolor parser and outputargument used from parser
        if GPU.gpu_clock != 'N/A':
            Plotsignals.append(Plotsignal("GPU Clock", "[MHz]", GPU.pstate_clock[-1], GPU.pstate_clock[0],
                                          "/pp_dpm_sclk", True, True, "#1f77b4",GPU.get_current_clock,0))
            Plotsignals.append(Plotsignal("GPU State", "[-]", len(GPU.pstate_clock)-1, 0,
                                          "/pp_dpm_sclk", True, True, "#ff7f0e",GPU.get_current_clock,1))
        if GPU.mem_clock != 'N/A':
            Plotsignals.append(Plotsignal("MEM Clock", "[MHz]", GPU.pmem_clock[-1], GPU.pmem_clock[0],
                                          "/pp_dpm_mclk", True, True, "#d62728",GPU.get_current_clock,0))
            Plotsignals.append(Plotsignal("MEM State", "[-]", len(GPU.pmem_clock)-1, 0,
                                          "/pp_dpm_mclk", True, True, "#9467bd",GPU.get_current_clock,1))

        self.add_available_signal(GPU.sensors, Plotsignals, hwmonpath=GPU.hwmonpath)

        # GPU busy percent only properly available in linux version 4.19+
        if (self.linux_kernelmain == 4 and self.linux_kernelsub > 18) or (self.linux_kernelmain >= 5):
            Plotsignals.append(Plotsignal("GPU Usage", "[-]", 100, 0, "/gpu_busy_percent", True, True, "#2ca02c", GPU.read_sensor))
        # as final check remove signals that return None:
        checked_plotlist = []
        for i, signal in enumerate(Plotsignals):
             signal.retrieve_data(self.maxpoints)
             if signal.get_last_value() is not None:
                 checked_plotlist.append(signal)
             else:
                 print(f"Removing {signal.name} from plotsignals, returning Nonetype")

        if len(checked_plotlist) == 0:
            print("Nothing to plot! Hiding the plot pane.")
            self.builder.get_object("Plot").hide()
        return checked_plotlist

    def add_available_signal(self, signals, Plotsignals, hwmonpath= "", subsystem = "", stop_recursion = False):
        for key, value in signals.items():
            if key in subsystem_unit_color:
                subsystem = key
                stop_recursion = False
            if "path" in value:
                if any(path_sensor_to_plot in value["path"] for path_sensor_to_plot in sensors_to_plot):
                    signallabel = value["path"][1:].split("_")[0]
                    signalmax = 0
                    signalmin = 0
                    signalpath = hwmonpath + value["path"]
                    if "min" in signals:
                        signalmin = signals['min']['value']
                        stop_recursion = True
                    if "max" in signals:
                        signalmax = signals['max']['value']
                        stop_recursion = True
                    if "crit" in signals:
                        signalmax = signals['crit']['value']
                        stop_recursion = True
                    if "label" in signals:
                        signallabel = signals["label"]["value"]
                        if signallabel == "vddgfx" and len(self.GPU.volt_range) > 0:
                            signalmax = self.GPU.volt_range[1]
                            signalmin = 0
                        stop_recursion = True
                    if "cap" in signals:
                        signalmax = signals["cap"]["value"]
                        stop_recursion = True
                    if "pwm" in value["path"]:
                        signalmax = 255
                        signallabel = "(fan)" + signallabel
                    Plotsignals.append(Plotsignal(signallabel, subsystem_unit_color[subsystem]["unit"],
                                                  signalmax,signalmin, signalpath, True, True,
                                                  subsystem_unit_color[subsystem]["color"], read))
            else:
                if not stop_recursion:
                    self.add_available_signal(value, Plotsignals, hwmonpath=hwmonpath, subsystem=subsystem, stop_recursion = stop_recursion)
                else:
                    continue

    def init_treeview(self):
        textrenderer = Gtk.CellRendererText()
        self.plotrenderer = Gtk.CellRendererToggle()
        self.plotrenderer.connect("toggled", self.on_plot_toggled)
        self.normaliserenderer = Gtk.CellRendererToggle()
        self.normaliserenderer.connect("toggled", self.on_normalise_toggled)
        self.tree = self.builder.get_object("Signal Selection")
        self.tree.append_column(Gtk.TreeViewColumn("Plot", self.plotrenderer, active=0))
        self.tree.append_column(Gtk.TreeViewColumn("Scale", self.normaliserenderer, active=1, activatable=2))
        columnnames=["Name","Unit","min","mean","max","current"]
        for i,column in enumerate(columnnames):
            tcolumn = Gtk.TreeViewColumn(column,textrenderer,text=i+3,foreground=9)
            self.tree.append_column(tcolumn)

        for plotsignal in self.Plotsignals:
            self.signalstore.append([plotsignal.plotenable, plotsignal.plotnormalise, True, plotsignal.name, convert_to_si(plotsignal.unit)[0], '0', '0', '0', '0', plotsignal.plotcolor])
        self.tree.set_model(self.signalstore)

    def update_signals(self):
        # Retrieve signal and set appropriate values in signalstore to update left pane in GUI
        for i,Plotsignal in enumerate(self.Plotsignals):
            Plotsignal.retrieve_data(self.maxpoints)
            disable_scaling = len(Plotsignal.get_values()) > 3 and Plotsignal.all_equal() and Plotsignal.plotnormalise and (Plotsignal.max == Plotsignal.min)
            self.signalstore[i][2] = not disable_scaling
            if disable_scaling:
                print(f"cannot scale values of {self.signalstore[i][3]} disabling scaling")
                self.on_normalise_toggled(self.normaliserenderer,i,disable_refresh=True)
                if disable_plots_if_scaling_error:
                    print(f"disabling {self.signalstore[i][3]} plot since disable_plots_if_scaling_error is set")
                    self.on_plot_toggled(self.plotrenderer,i)
            self.signalstore[i][5]=str(np.around(convert_to_si(Plotsignal.unit, Plotsignal.get_min())[1], self.precision))
            self.signalstore[i][6]=str(np.around(convert_to_si(Plotsignal.unit,Plotsignal.get_mean())[1],self.precision))
            self.signalstore[i][7]=str(np.around(convert_to_si(Plotsignal.unit,Plotsignal.get_max())[1],self.precision))
            self.signalstore[i][8]=str(np.around(convert_to_si(Plotsignal.unit,Plotsignal.get_last_value())[1],self.precision))

    def on_plot_toggled(self, widget, path, disable_refresh=False):
        self.signalstore[path][0] = not self.signalstore[path][0]
        self.Plotsignals[int(path)].plotenable = not self.Plotsignals[int(path)].plotenable
        if not disable_refresh:
            self.update_plot()

    def on_normalise_toggled(self, widget, path, disable_refresh=False):
        self.signalstore[path][1] = not self.signalstore[path][1]
        self.Plotsignals[int(path)].plotnormalise = not self.Plotsignals[int(path)].plotnormalise
        if not disable_refresh:
            self.update_plot()

    def update_plot(self):
        if len(self.Plotsignals) == 0:
            return
        self.ax.clear()
        for Plotsignal in self.Plotsignals:
            if Plotsignal.plotenable:
                if Plotsignal.plotnormalise:
                    data = Plotsignal.get_normalised_values()*100
                    self.ax.plot(data, color=Plotsignal.plotcolor)
                else:
                    data = Plotsignal.get_values()
                    self.ax.plot(convert_to_si(Plotsignal.unit,data)[1], color=Plotsignal.plotcolor)


        self.ax.grid(True)
        self.ax.get_yaxis().tick_right()
        self.ax.get_yaxis().set_label_position("right")
        self.ax.get_yaxis().set_visible(True)
        self.ax.get_xaxis().set_visible(False)
        all_normalised = True
        all_same_unit = True
        unit = ""
        iter = self.signalstore.get_iter(0)
        while iter is not None:
            if self.signalstore[iter][0] == True:
                if unit == "":
                    unit = self.signalstore[iter][4]
                if self.signalstore[iter][1] == False:
                    all_normalised = False
                if self.signalstore[iter][4] != unit:
                    all_same_unit = False
            if not all_normalised and not all_same_unit:
                break
            iter = self.signalstore.iter_next(iter)
        if all_normalised:
            self.ax.set_yticks(np.arange(0, 101, step=25))
            self.ax.set_ylabel('Percent [%]')
        else:
            self.ax.yaxis.set_major_locator(AutoLocator())
            if all_same_unit:
                self.ax.set_ylabel(unit)
            else:
                self.ax.set_ylabel("")
        self.canvas.draw()
        self.canvas.flush_events()

    def refresh(self):
        # This is run in thread
        self.update_signals()
        self.update_plot()
