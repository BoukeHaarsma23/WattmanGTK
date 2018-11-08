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

import gi                   # required for GTK3
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk

class Handler:
    # Handles all interaction with the GUI and Functions
    # TODO add FAN controls
    # TODO add TEMP controls
    # TODO BUG: make UI stack when width is small
    # TODO BUG: weird redrawing issue on changing panes
    # TODO BUG: sometimes main window has different tints of grey?
    # TODO proper scrollbars
    # TODO implement POLKIT for writing as root, for now --> export bash script
    # TODO implement reboot persistance
    # TODO decrease number of typecastings used
    def __init__(self, builder, GPU):
        self.builder = builder
        self.GPU = GPU
        self.set_maximum_values()
        self.set_initial_values()
        self.update_gui()
        # TODO implement POLKIT for writing as root, for now --> disable button
        self.builder.get_object("Lock").set_sensitive(False)

    def set_maximum_values(self):
        # Sets maximum values for all elements and shows relevant sliders
        if self.GPU.pstate:
            for i,_ in enumerate(self.GPU.pstate_clock):
                # GPU
                self.builder.get_object("GPU state " + str(i)).show()
                self.builder.get_object("Pstate voltage " + str(i)).show()
                self.builder.get_object("GPU P Frequency " + str(i)).set_lower(self.GPU.pstate_clockrange[0])
                self.builder.get_object("GPU P Frequency " + str(i)).set_upper(self.GPU.pstate_clockrange[1])
            for i,_ in enumerate(self.GPU.pmem_clock):
                # MEMORY
                self.builder.get_object("MEM state " + str(i)).show()
                self.builder.get_object("MPstate voltage " + str(i)).show()
                self.builder.get_object("MEM P Frequency " + str(i)).set_lower(self.GPU.pmem_clockrange[0])
                self.builder.get_object("MEM P Frequency " + str(i)).set_upper(self.GPU.pmem_clockrange[1])

        if self.GPU.power_cap is not None:
            self.builder.get_object("Pow Target Slider").set_upper(self.GPU.power_cap_max)
            self.builder.get_object("Pow Target Slider").set_lower(self.GPU.power_cap_min)

    def set_initial_values(self):
        # Sets values in program as read currently in the system
        if self.GPU.pstate:
            for i,_ in enumerate(self.GPU.pstate_clock):
                # GPU
                self.builder.get_object("GPU P Frequency " + str(i)).set_value(self.GPU.pstate_clock[i])
                self.builder.get_object("GPU manual state " + str(i)).set_text(str(self.GPU.pstate_clock[i]))
                self.builder.get_object("Pstate voltage " + str(i)).set_text(str(self.GPU.pstate_voltage[i]))
            for i,_ in enumerate(self.GPU.pmem_clock):
                # MEMORY
                self.builder.get_object("MEM P Frequency " + str(i)).set_value(self.GPU.pmem_clock[i])
                self.builder.get_object("MEM manual state " + str(i)).set_text(str(self.GPU.pmem_clock[i]))
                self.builder.get_object("MPstate voltage " + str(i)).set_text(str(self.GPU.pmem_voltage[i]))

        # Frequency sliders
        self.builder.get_object("GPU Target").set_value(self.GPU.read_sensor("/pp_sclk_od"))
        self.builder.get_object("MEM Target").set_value(self.GPU.read_sensor("/pp_mclk_od"))

        if self.GPU.power_cap is not None:
            self.builder.get_object("Pow Target").set_value(self.GPU.power_cap)
            self.builder.get_object("Powerlimit Label").set_text("Power limit " + str(self.builder.get_object("Pow Target").get_value()) + "(W)\nAutomatic")
        else:
            self.builder.get_object("Pow Target").set_visible = False
            self.builder.get_object("Powerlimit Label").set_visible = False

        # Manual/auto switches and run associated functions
        # TODO: possible to read manual states separately?
        self.init_manual_mode = self.GPU.read_sensor_str("/power_dpm_force_performance_level") == "manual"

        self.builder.get_object("GPU Frequency auto switch").set_state(self.init_manual_mode)
        self.set_GPU_Frequency_Switch(self.builder.get_object("GPU Frequency auto switch"), self.init_manual_mode)

        if self.GPU.pstate:
            self.builder.get_object("GPU Voltage auto switch").set_state(self.init_manual_mode)
            self.set_GPU_Voltage_Switch(self.builder.get_object("GPU Voltage auto switch"), self.init_manual_mode)
        else:
            self.builder.get_object("GPU Frequency auto switch").set_sensitive(False)
            self.builder.get_object("GPU Voltage auto switch").set_sensitive(False)

        self.builder.get_object("MEM Frequency auto switch").set_state(self.init_manual_mode)
        self.set_MEM_Frequency_Switch(self.builder.get_object("MEM Frequency auto switch"), self.init_manual_mode)

        if self.GPU.pstate:
            self.builder.get_object("MEM Voltage auto switch").set_state(self.init_manual_mode)
            self.set_MEM_Voltage_Switch(self.builder.get_object("MEM Voltage auto switch"), self.init_manual_mode)
        else:
            self.builder.get_object("MEM Frequency auto switch").set_sensitive(False)
            self.builder.get_object("MEM Voltage auto switch").set_sensitive(False)

        if self.GPU.power_cap is None:
            self.builder.get_object("POW auto switch").set_sensitive(False)
        else:
            self.builder.get_object("POW auto switch").set_state(self.init_manual_mode)
            self.set_Powerlimit_Switch(self.builder.get_object("POW auto switch"),self.init_manual_mode)

        # set new manual mode to initial mode to determine when changes need to be applied
        self.new_manual_mode=self.init_manual_mode

        # disable Revert/apply button since this is the setting already used in the system now
        self.builder.get_object("Revert").set_visible(False)
        self.builder.get_object("Apply").set_visible(False)

    def update_gui(self):
        # Update gui with new GPU values
        self.GPU.get_currents()
        self.builder.get_object("Current GPU Speed").set_text("Current speed\n" + str(self.GPU.gpu_clock) + " MHz\n(State: " + str(self.GPU.gpu_state) + ")")
        self.builder.get_object("Current MEM Speed").set_text("Current speed\n" + str(self.GPU.mem_clock) + " MHz\n(State: " + str(self.GPU.mem_state) + ")")
        self.builder.get_object("Current FAN Speed").set_text("Current speed\n" + str(self.GPU.fan_speed) + " RPM")
        self.builder.get_object("Current TEMP").set_text("Current temperature\n" + str(self.GPU.temperature) + " °C")

        self.builder.get_object("GPU utilisation").set_fraction(self.GPU.gpu_clock_utilisation)
        self.builder.get_object("MEM utilisation").set_fraction(self.GPU.mem_utilisation)
        self.builder.get_object("FAN utilisation").set_fraction(self.GPU.fan_speed_utilisation)
        self.builder.get_object("Temp utilisation").set_fraction(self.GPU.temp_utilisation)

    def set_Slider(self, slider):
        # Run after user used a slider for GPU/MEM states
        id = Gtk.Buildable.get_name(slider)
        system = id[:3]
        state = int(id[-1])
        prev_slider = self.builder.get_object(id[0:-1] + str(state - 1))
        next_slider = self.builder.get_object(id[0:-1] + str(state + 1))
        value = int(slider.get_value())
        slider.set_value(value)
        if prev_slider is not None:
            prev_value = prev_slider.get_value()
            if value < prev_value:
                prev_slider.set_value(value)
                self.set_Slider(prev_slider)
        if next_slider is not None and next_slider.get_sensitive() == True:
            next_value = next_slider.get_value()
            if value > next_value:
                next_slider.set_value(value)
                self.set_Slider(next_slider)
        self.builder.get_object(system + " manual state " + str(state)).set_text(str(value))
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_GPU_Percent_overclock(self, slider):
        # Run after user used the % slider on the GPU
        value = int(slider.get_value())
        for i,_ in enumerate(self.GPU.pstate_clock):
            current_object = self.builder.get_object("GPU P Frequency " + str(i))
            start_value = self.GPU.pstate_clock[i]
            if self.GPU.pstate:
                if start_value + value < self.GPU.pstate_clockrange[1]:
                    current_object.set_value(start_value + (value / 100) * start_value)
                else:
                    current_object.set_value(self.GPU.pstate_clockrange[1])

        # set pretty labels
        if value != 0:
            self.builder.get_object("GPU Frequency Label").set_text("Frequency " + str(value) + "(%)\nautomatic")
        else:
            self.builder.get_object("GPU Frequency Label").set_text("Frequency (%)\nautomatic")
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_MEM_Percent_overclock(self, slider):
        # Run after user used the % slider on the MEM
        value = int(slider.get_value())
        for i in range(len(self.GPU.pmem_clock)):
            current_object = self.builder.get_object("MEM P Frequency " + str(i))
            start_value = self.GPU.pmem_clock[i]
            if self.GPU.pstate:
                if start_value + value < self.GPU.pmem_clockrange[1]:
                    current_object.set_value(start_value + (value / 100) * start_value)
                else:
                    current_object.set_value(self.GPU.pstate_clockrange[1])

        # set pretty labels
        if value != 0:
            self.builder.get_object("MEM Frequency Label").set_text("Frequency " + str(value) + "(%)\nautomatic")
        else:
            self.builder.get_object("MEM Frequency Label").set_text("Frequency (%)\nautomatic")
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_POW_slider(self, slider):
        # Run after user used the % slider on the power slider
        value = int(slider.get_value())
        slider.set_value(value)
        self.builder.get_object("Powerlimit Label").set_text("Power limit " + str(value) + "(W)\nManual")
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_GPU_Voltage_Switch(self, switch, value):
        # Run after user switches the voltage switch on the GPU side
        if value:
            self.builder.get_object("GPU Voltage Label").set_text("Voltage Control (mV)\nmanual")
            [self.builder.get_object("Pstate voltage " + str(i)).set_text(str(self.GPU.pstate_voltage[i])) for i,_ in enumerate(self.GPU.pstate_clock)]
        else:
            self.builder.get_object("GPU Voltage Label").set_text("Voltage Control (mV)\nautomatic")
            [self.builder.get_object("Pstate voltage " + str(i)).set_text("auto") for i,_ in enumerate(self.GPU.pstate_clock)]
        for i,_ in enumerate(self.GPU.pstate_clock):
            self.builder.get_object("Pstate voltage " + str(i)).set_sensitive(value)
        switch.set_state(value)
        if self.builder.get_object("MEM Voltage auto switch").get_state() != value:
            self.set_MEM_Voltage_Switch(self.builder.get_object("MEM Voltage auto switch"),value)
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_GPU_Frequency_Switch(self, switch, value):
        # Run after user switches the frequency switch on the GPU side
        if value:
            for i,_ in enumerate(self.GPU.pstate_clock):
                self.builder.get_object("GPU manual state " + str(i)).show()
                self.builder.get_object("GPU state " + str(i)).set_sensitive(value)
            self.builder.get_object("GPU Target").hide()
            self.builder.get_object("GPU Frequency Label").set_text("Frequency (MHz)\ndynamic")
        else:
            for i,_ in enumerate(self.GPU.pstate_clock):
                self.builder.get_object("GPU manual state " + str(i)).hide()
                self.builder.get_object("GPU state " + str(i)).set_sensitive(value)
            gpu_target = self.builder.get_object("GPU Target")
            gpu_target.show()
            self.set_GPU_Percent_overclock(gpu_target)
            if int(gpu_target.get_value()) == 0:
                self.builder.get_object("GPU Frequency Label").set_text("Frequency (%)\nautomatic")
            else:
                self.builder.get_object("GPU Frequency Label").set_text("Frequency " + str(int(gpu_target.get_value())) + "(%)\nautomatic")
        switch.set_state(value)
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_MEM_Voltage_Switch(self, switch, value):
        # Run after user switches the voltage switch on the MEM side
        if value:
            self.builder.get_object("MEM Voltage Label").set_text("Voltage Control (mV)\nmanual")
            [self.builder.get_object("MPstate voltage " + str(i)).set_text(str(self.GPU.pmem_voltage[i])) for i,_ in enumerate(self.GPU.pmem_voltage)]
        else:
            self.builder.get_object("MEM Voltage Label").set_text("Voltage Control (mV)\nautomatic")
            [self.builder.get_object("MPstate voltage " + str(i)).set_text("auto") for i,_ in enumerate(self.GPU.pmem_voltage)]
        for i in range(len(self.GPU.pmem_clock)):
            self.builder.get_object("MPstate voltage " + str(i)).set_sensitive(value)
        switch.set_state(value)
        if self.builder.get_object("GPU Voltage auto switch").get_state() != value:
            self.set_GPU_Voltage_Switch(self.builder.get_object("GPU Voltage auto switch"),value)
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_MEM_Frequency_Switch(self, switch, value):
        # Run after user switches the frequency switch on the MEM side
        if value:
            for i in range(len(self.GPU.pmem_clock)):
                self.builder.get_object("MEM manual state " + str(i)).show()
                self.builder.get_object("MEM state " + str(i)).set_sensitive(value)
            self.builder.get_object("MEM Target").hide()
            self.builder.get_object("MEM Frequency Label").set_text("Frequency (MHz)\ndynamic")
        else:
            for i in range(len(self.GPU.pmem_clock)):
                self.builder.get_object("MEM manual state " + str(i)).hide()
                self.builder.get_object("MEM state " + str(i)).set_sensitive(value)
            mem_target = self.builder.get_object("MEM Target")
            mem_target.show()
            self.set_MEM_Percent_overclock(mem_target)
            if int(mem_target.get_value()) == 0:
                self.builder.get_object("MEM Frequency Label").set_text("Frequency (%)\nautomatic")
            else:
                self.builder.get_object("MEM Frequency Label").set_text("Frequency " + str(int(mem_target.get_value())) + "(%)\nautomatic")
        switch.set_state(value)
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_Powerlimit_Switch(self, switch, value):
        # Run after user switches the power switch on the powerlimit
        self.builder.get_object("Pow Target").set_sensitive(value)
        if value:
            self.builder.get_object("Powerlimit Label").set_text("Power limit " + str(self.builder.get_object("Pow Target").get_value()) + "(W)\nmanual")
        else:
            self.builder.get_object("Powerlimit Label").set_text("Power limit " + str(self.builder.get_object("Pow Target").get_value()) + "(W)\nautomatic")
            self.builder.get_object("Pow Target").set_value(self.GPU.power_cap)
        switch.set_state(value)
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def process_Edit(self, entry):
        # run after each textbox is edited
        try:
            value = int(entry.get_text())
            id = Gtk.Buildable.get_name(entry)
            system = id[:4]
            state = int(id[-1])
            if "GPU" in system:
                slider = self.builder.get_object("GPU state " + str(state))
                if value < self.GPU.pstate_clockrange[0]:
                    value = self.GPU.pstate_clockrange[0]
                elif value > self.GPU.pstate_clockrange[1]:
                    value = self.GPU.pstate_clockrange[1]
                slider.set_value(value)
                self.set_Slider(slider)
                self.builder.get_object("Revert").set_sensitive(self.check_change())
                self.builder.get_object("Apply").set_sensitive(self.check_change())
            elif "MEM" in system:
                slider = self.builder.get_object("MEM state " + str(state))
                if value < self.GPU.pmem_clockrange[0]:
                    value = self.GPU.pmem_clockrange[0]
                elif value > self.GPU.pmem_clockrange[1]:
                    value = self.GPU.pmem_clockrange[1]
                slider.set_value(value)
                self.set_Slider(slider)
                self.builder.get_object("Revert").set_sensitive(self.check_change())
                self.builder.get_object("Apply").set_sensitive(self.check_change())
            elif "FAN" in system:
                # TODO make fan controls available
                self.builder.get_object("Revert").set_sensitive(self.check_change())
                self.builder.get_object("Apply").set_sensitive(self.check_change())
            elif "TEMP" in system:
                # TODO make temp controls available
                self.builder.get_object("Revert").set_sensitive(self.check_change())
                self.builder.get_object("Apply").set_sensitive(self.check_change())
            elif "voltage" in id:
                # GPU/MEM voltage
                if value < self.GPU.volt_range[0]:
                    value = self.GPU.volt_range[0]
                elif value > self.GPU.volt_range[1]:
                    value = self.GPU.volt_range[1]
                entry.set_text(str(value))
                self.builder.get_object("Revert").set_visible(self.check_change())
                self.builder.get_object("Apply").set_visible(self.check_change())
            else:
                # I don"t know what this textbox belongs to
                entry.set_text("Error")
                self.builder.get_object("Revert").set_visible(True)
                self.builder.get_object("Apply").set_visible(False)
        except:
            entry.set_text("Error")
            self.builder.get_object("Revert").set_visible(True)
            self.builder.get_object("Apply").set_visible(False)

    def check_change(self):
        # check if any manual slider is set
        if (self.builder.get_object("GPU Frequency auto switch").get_state() or
                self.builder.get_object("GPU Voltage auto switch").get_state() or
                self.builder.get_object("MEM Frequency auto switch").get_state() or
                self.builder.get_object("MEM Voltage auto switch").get_state() or
                self.builder.get_object("POW auto switch").get_state()):
            # manual mode
            self.new_manual_mode = True
        else:
            # set new manual to automatic when everything is auto
            self.new_manual_mode = False

        # if change here, new values have to be written anyway
        if self.new_manual_mode != self.init_manual_mode:
            # manual --> auto or auto --> manual
            return True
        elif not (self.init_manual_mode):
            # going auto --> auto so no change in switches, but in OC percentages?
            if (self.GPU.read_sensor("/pp_sclk_od") != self.builder.get_object("GPU Target").get_value()) or (
                    self.GPU.read_sensor("/pp_mclk_od") != self.builder.get_object("MEM Target").get_value()):
                return True
            else:
                return False

        # so manual --> manual, Check in change of all clock/voltage/switches values
        # TODO
        # for now, return true
        return True


    def onDestroy(self, *args):
        # On pressing close button
        Gtk.main_quit()

    def unlock(self, button):
        # On pressing lock/unlock button
        # TODO ask for root permissions using polkit
        print("Unlock")

    def apply(self, button):
        # TODO write proper GUI apply function with confirm
        # Documentation: https://dri.freedesktop.org/docs/drm/gpu/amdgpu.html
        print("\n\n\n\n")
        print("------------------ CAUTION ---------------")
        print("This version does not support applying settings from the GUI yet, this will be a future addition. ")
        print("!!!This also gives you the opportunity to look over the settings generated by this program!!!")
        print("You can find the settings that would be written in \"Set_WattmanGTK_Settings.sh\" file. ")
        print("To apply this file you first have to make it executable, by using \"chmod +x Set_WattmanGTK_Settings.sh\" (without quotes)")
        print("Then to actually apply the settings type in the terminal here \"sudo ./Set_WattmanGTK_Settings.sh\" (without quotes) ")
        print("Please note that this may damage your graphics card, so use at your own risk!")
        print("------------------ CAUTION ---------------")
        print("\n\n\n\n")
        outputfile = open("Set_WattmanGTK_Settings.sh","w+")
        outputfile.write("#!/bin/bash\n")
        if self.new_manual_mode:
            mode = "manual"
        else:
            mode = "auto"

        # Powermode
        outputfile.write("echo \"" + mode + "\" > " + self.GPU.cardpath + "/power_dpm_force_performance_level\n" )

        # Powercap
        if self.builder.get_object("POW auto switch").get_state():
            outputfile.write("echo " + str(int(self.builder.get_object("Pow Target").get_value() * 1000000)) + " > " + self.GPU.powersensors.get_attribute_path('_cap',True) + "\n")

        # GPU P states
        # TODO REFACTOR
        if self.builder.get_object("GPU Frequency auto switch").get_state() and self.builder.get_object("GPU Voltage auto switch").get_state():
            # all manual
            for i, _ in enumerate(self.GPU.pstate_clock):
                #   "s state clock voltage"
                # echo "s 0 300 750" > /sys/class/drm/card0/device/pp_od_clk_voltage
                outputfile.write("echo \"s " + str(i) + " " +
                                 str(int(self.builder.get_object("GPU state " + str(i)).get_value())) + " " +
                                 self.builder.get_object("Pstate voltage " + str(i)).get_text() +
                                 "\" > " + self.GPU.cardpath + "/pp_od_clk_voltage" +
                                 "\n" )
            outputfile.write("echo \"c\" > " + self.GPU.cardpath + "/pp_od_clk_voltage\n")
        elif not self.builder.get_object("GPU Frequency auto switch").get_state() and self.builder.get_object("GPU Voltage auto switch").get_state():
            # frequency set to auto
            for i, _ in enumerate(self.GPU.pstate_clock):
                #   "s state clock voltage"
                # echo "s 0 300 750" > /sys/class/drm/card0/device/pp_od_clk_voltage
                outputfile.write("echo \"s " + str(i) + " " +
                                 str(int(self.builder.get_object("GPU state " + str(i)).get_value())) + " " +
                                 self.builder.get_object("Pstate voltage " + str(i)).get_text() +
                                 "\" > " + self.GPU.cardpath + "/pp_od_clk_voltage" +
                                 "\n" )
            outputfile.write("echo \"c\" > " + self.GPU.cardpath + "/pp_od_clk_voltage\n")
        elif self.builder.get_object("GPU Frequency auto switch").get_state() and not self.builder.get_object("GPU Voltage auto switch").get_state():
            # voltage set to auto
            for i, _ in enumerate(self.GPU.pstate_clock):
                #   "s state clock voltage"
                # echo "s 0 300 750" > /sys/class/drm/card0/device/pp_od_clk_voltage
                outputfile.write("echo \"s " + str(i) + " " +
                                 str(int(self.builder.get_object("GPU state " + str(i)).get_value())) + " " +
                                 str(self.GPU.pstate_voltage[i]) +
                                 "\" > " + self.GPU.cardpath + "/pp_od_clk_voltage" +
                                 "\n" )
            outputfile.write("echo \"c\" > " + self.GPU.cardpath + "/pp_od_clk_voltage\n")

        # MEM states
        # TODO REFACTOR
        if self.builder.get_object("MEM Frequency auto switch").get_state() and self.builder.get_object("MEM Voltage auto switch").get_state():
            # all manual
            for i, _ in enumerate(self.GPU.pmem_clock):
                #   "m state clock voltage"
                # echo "m 0 300 750" > /sys/class/drm/card0/device/pp_od_clk_voltage
                outputfile.write("echo \"m " + str(i) + " " +
                                 str(int(self.builder.get_object("MEM state " + str(i)).get_value())) + " " +
                                 self.builder.get_object("MPstate voltage " + str(i)).get_text() +
                                 "\" > " + self.GPU.cardpath + "/pp_od_clk_voltage" +
                                 "\n" )
            outputfile.write("echo \"c\" > " + self.GPU.cardpath + "/pp_od_clk_voltage\n")
        elif not self.builder.get_object("MEM Frequency auto switch").get_state() and self.builder.get_object("MEM Voltage auto switch").get_state():
            # frequency set to auto
            for i, _ in enumerate(self.GPU.pmem_clock):
                #   "m state clock voltage"
                # echo "m 0 300 750" > /sys/class/drm/card0/device/pp_od_clk_voltage
                outputfile.write("echo \"m " + str(i) + " " +
                                 str(int(self.builder.get_object("MEM state " + str(i)).get_value())) + " " +
                                 self.builder.get_object("MPstate voltage " + str(i)).get_text() +
                                 "\" > " + self.GPU.cardpath + "/pp_od_clk_voltage" +
                                 "\n" )
            outputfile.write("echo \"c\" > " + self.GPU.cardpath + "/pp_od_clk_voltage\n")
        elif self.builder.get_object("MEM Frequency auto switch").get_state() and not self.builder.get_object("MEM Voltage auto switch").get_state():
            # voltage set to auto
            for i, _ in enumerate(self.GPU.pmem_clock):
                #   "s state clock voltage"
                # echo "m 0 300 750" > /sys/class/drm/card0/device/pp_od_clk_voltage
                outputfile.write("echo \"m " + str(i) + " " +
                                 str(int(self.builder.get_object("MEM state " + str(i)).get_value())) + " " +
                                 str(self.GPU.pmem_voltage[i]) +
                                 "\" > " + self.GPU.cardpath + "/pp_od_clk_voltage" +
                                 "\n" )
            outputfile.write("echo \"c\" > " + self.GPU.cardpath + "/pp_od_clk_voltage\n")

        # GPU % overclock
        SCLK_OD = int(self.builder.get_object("GPU Target").get_value())
        if not self.builder.get_object("GPU Frequency auto switch").get_state() and (SCLK_OD != self.GPU.read_sensor("/pp_sclk_od")):
            outputfile.write("echo " + str(SCLK_OD) + " > " + self.GPU.cardpath + "/pp_sclk_od\n")

        # MEM % overclock
        MCLK_OD = int(self.builder.get_object("MEM Target").get_value())
        if not self.builder.get_object("MEM Frequency auto switch").get_state() and (MCLK_OD != self.GPU.read_sensor("/pp_mclk_od")):
            outputfile.write("echo " + str(MCLK_OD) + " > " + self.GPU.cardpath + "/pp_mclk_od\n")

        outputfile.close()
        exit()

    def revert(self, button):
        # On pressing revert button
        self.set_initial_values()

    def on_menu_about_clicked(self, menuitem):
        # On pressing about menu item
        self.builder.get_object("About").run()
        self.builder.get_object("About").hide()
