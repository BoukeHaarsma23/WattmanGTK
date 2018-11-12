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
    def __init__(self, builder, GPUs):
        self.builder = builder
        self.GPUs = GPUs
        self.GPU = GPUs[0]
        self.init_state = {}
        self.set_maximum_values()
        self.set_initial_values()
        self.init_state = self.create_state_dict()
        self.update_gui()

        # initialise GPU selection combobox
        textrenderer = Gtk.CellRendererText()
        self.gpustore = Gtk.ListStore(str)
        for i, card in enumerate(GPUs):
            self.gpustore.append([f"{i+1}: {card.fancyname}"])
        combobox = self.builder.get_object("GPU Selection")
        combobox.set_model(self.gpustore)
        combobox.pack_start(textrenderer, True)
        combobox.add_attribute(textrenderer, "text", 0)
        combobox.set_entry_text_column(0)
        combobox.set_active(0)
        combobox.connect("changed", self.on_GPU_changed)

        # TODO implement POLKIT for writing as root, for now --> disable button
        self.builder.get_object("Lock").set_sensitive(False)

    def on_GPU_changed(self, combo):
        selected_GPU = combo.get_active()
        print(f"Changing GPU to {self.GPUs[selected_GPU].fancyname}")
        self.GPU = self.GPUs[selected_GPU]
        self.set_maximum_values()
        self.set_initial_values()
        self.update_gui()

    def set_maximum_values(self):
        # Sets maximum values for all elements and shows relevant sliders
        if self.GPU.pstate:
            for i,_ in enumerate(self.GPU.pstate_clock):
                # GPU
                self.builder.get_object(f"GPU state {i}").show()
                self.builder.get_object(f"Pstate voltage {i}").show()
                self.builder.get_object(f"GPU P Frequency {i}").set_lower(self.GPU.pstate_clockrange[0])
                self.builder.get_object(f"GPU P Frequency {i}").set_upper(self.GPU.pstate_clockrange[1])
            for i,_ in enumerate(self.GPU.pmem_clock):
                # MEMORY
                self.builder.get_object(f"MEM state {i}").show()
                self.builder.get_object(f"MPstate voltage {i}").show()
                self.builder.get_object(f"MEM P Frequency {i}").set_lower(self.GPU.pmem_clockrange[0])
                self.builder.get_object(f"MEM P Frequency {i}").set_upper(self.GPU.pmem_clockrange[1])

        if self.GPU.power_cap is not None:
            self.builder.get_object("Pow Target Slider").set_upper(self.GPU.power_cap_max)
            self.builder.get_object("Pow Target Slider").set_lower(self.GPU.power_cap_min)
        if self.GPU.fan_target is not None:
            for target in ["Min", "Target"]:
                self.builder.get_object(f"FAN RPM {target}").set_lower(self.GPU.fan_target_range[0])
                self.builder.get_object(f"FAN RPM {target}").set_upper(self.GPU.fan_target_range[1])

    def set_initial_values(self):
        # Sets values in program as read currently in the system
        if self.GPU.pstate:
            for i,_ in enumerate(self.GPU.pstate_clock):
                # GPU
                self.builder.get_object(f"GPU P Frequency {i}").set_value(self.GPU.pstate_clock[i])
                self.builder.get_object(f"GPU manual state {i}").set_text(str(self.GPU.pstate_clock[i]))
                self.builder.get_object(f"Pstate voltage {i}").set_text(str(self.GPU.pstate_voltage[i]))
            for i,_ in enumerate(self.GPU.pmem_clock):
                # MEMORY
                self.builder.get_object(f"MEM P Frequency {i}").set_value(self.GPU.pmem_clock[i])
                self.builder.get_object(f"MEM manual state {i}").set_text(str(self.GPU.pmem_clock[i]))
                self.builder.get_object(f"MPstate voltage {i}").set_text(str(self.GPU.pmem_voltage[i]))

        # Frequency sliders
        self.builder.get_object("GPU Target").set_value(self.GPU.read_sensor("pp_sclk_od"))
        self.builder.get_object("MEM Target").set_value(self.GPU.read_sensor("pp_mclk_od"))

        if self.GPU.power_cap is not None:
            self.builder.get_object("Pow Target").set_value(self.GPU.power_cap)
            self.builder.get_object("Powerlimit Label").set_text(f"Power limit {self.GPU.power_cap} (W)\nAutomatic")
        else:
            self.builder.get_object("Pow Target").set_visible = False
            self.builder.get_object("Powerlimit Label").set_visible = False

        # Manual/auto switches and run associated functions
        # TODO: possible to read manual states separately?
        manual_mode = self.GPU.read_sensor("power_dpm_force_performance_level") == "manual"

        self.builder.get_object("GPU Frequency auto switch").set_state(manual_mode)
        self.set_GPU_Frequency_Switch(self.builder.get_object("GPU Frequency auto switch"), manual_mode)

        if self.GPU.pstate:
            self.builder.get_object("GPU Voltage auto switch").set_state(manual_mode)
            self.set_GPU_Voltage_Switch(self.builder.get_object("GPU Voltage auto switch"), manual_mode)
        else:
            self.builder.get_object("GPU Frequency auto switch").set_sensitive(False)
            self.builder.get_object("GPU Voltage auto switch").set_sensitive(False)

        self.builder.get_object("MEM Frequency auto switch").set_state(manual_mode)
        self.set_MEM_Frequency_Switch(self.builder.get_object("MEM Frequency auto switch"), manual_mode)

        if self.GPU.pstate:
            self.builder.get_object("MEM Voltage auto switch").set_state(manual_mode)
            self.set_MEM_Voltage_Switch(self.builder.get_object("MEM Voltage auto switch"), manual_mode)
        else:
            self.builder.get_object("MEM Frequency auto switch").set_sensitive(False)
            self.builder.get_object("MEM Voltage auto switch").set_sensitive(False)

        if self.GPU.power_cap is None:
            self.builder.get_object("POW auto switch").set_sensitive(False)
        else:
            self.builder.get_object("POW auto switch").set_state(manual_mode)
            self.set_Powerlimit_Switch(self.builder.get_object("POW auto switch"),manual_mode)

        if self.GPU.fan_control_value is None:
            self.builder.get_object("FAN auto switch").set_sensitive(False)
        else:
            state = False if self.GPU.fan_control_value[0] == 2 else True
            self.builder.get_object("FAN auto switch").set_state(state)
            self.set_FAN_Switch(self.builder.get_object("FAN auto switch"),state)
            self.builder.get_object("FAN RPM Min").set_value(self.GPU.fan_target_min[0])
            self.builder.get_object("FAN RPM Target").set_value(self.GPU.fan_target[0])

        # disable Revert/apply button since this is the setting already used in the system now
        self.builder.get_object("Revert").set_visible(False)
        self.builder.get_object("Apply").set_visible(False)

    def create_state_dict(self):
        state = dict()
        state['manual_mode'] = (self.builder.get_object("GPU Frequency auto switch").get_state() or
                self.builder.get_object("GPU Voltage auto switch").get_state() or
                self.builder.get_object("MEM Frequency auto switch").get_state() or
                self.builder.get_object("MEM Voltage auto switch").get_state() or
                self.builder.get_object("POW auto switch").get_state())
        #GPU
        if self.GPU.pstate:
            for i,_ in enumerate(self.GPU.pstate_clock):
                state[f"GPU P Frequency {i}"] = self.builder.get_object(f"GPU P Frequency {i}").get_value()
                state[f"Pstate voltage {i}"] = self.builder.get_object(f"Pstate voltage {i}").get_text()
            for i,_ in enumerate(self.GPU.pmem_clock):
                state[f"MEM P Frequency {i}"] = self.builder.get_object(f"MEM P Frequency {i}").get_value()
                state[f"MPstate voltage {i}"] = self.builder.get_object(f"MPstate voltage {i}").get_text()
        # Frequency sliders
        state['GPU Target'] = self.builder.get_object("GPU Target").get_value()
        state['MEM Target'] = self.builder.get_object("MEM Target").get_value()
        #FAN
        state['FAN auto switch'] = self.builder.get_object("FAN auto switch").get_state()
        state['FAN RPM Min'] = self.builder.get_object("FAN RPM Min").get_value()
        state['FAN RPM Target'] = self.builder.get_object("FAN RPM Target").get_value()
        #TEMP

        #Power
        state["Pow Target Slider"] = self.builder.get_object("Pow Target Slider").get_value()
        state["POW auto switch"] = self.builder.get_object("POW auto switch").get_active()
        return state

    def update_gui(self):
        # Update gui with new GPU values
        self.GPU.get_currents()
        self.builder.get_object("Current GPU Speed").set_text("Current speed\n %d MHz\n(State: %i)" % (self.GPU.gpu_clock, self.GPU.gpu_state))
        self.builder.get_object("Current MEM Speed").set_text("Current speed\n %d MHz\n(State: %i)" % (self.GPU.mem_clock,self.GPU.mem_state))
        self.builder.get_object("Current FAN Speed").set_text("Current speed\n %d RPM" % self.GPU.fan_speed)
        self.builder.get_object("Current TEMP").set_text("Current temperature\n %.1f °C" % self.GPU.temperature)

        self.builder.get_object("GPU utilisation").set_fraction(self.GPU.gpu_clock_utilisation)
        self.builder.get_object("MEM utilisation").set_fraction(self.GPU.mem_utilisation)
        self.builder.get_object("FAN utilisation").set_fraction(self.GPU.fan_speed_utilisation)
        self.builder.get_object("Temp utilisation").set_fraction(self.GPU.temp_utilisation)

    def set_Slider(self, slider):
        # Run after user used a slider for GPU/MEM states
        id = Gtk.Buildable.get_name(slider)
        system = id[:4].rstrip()
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
        self.builder.get_object(f"{system} manual state {state}").set_text(str(value))
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_percent_overclock(self,slider,subsystem):
        value = int(slider.get_value())
        if subsystem == "GPU":
            clocks = self.GPU.pstate_clock
            max_value = self.GPU.pstate_clockrange[1]
        elif subsystem == "MEM":
            clocks = self.GPU.pmem_clock
            max_value = self.GPU.pmem_clockrange[1]
        for i, clock in enumerate(clocks):
            current_object = self.builder.get_object(f"{subsystem} P Frequency {i}")
            start_value = clock
            if self.GPU.pstate:
                if start_value + value < max_value:
                    current_object.set_value(start_value + (value / 100) * start_value)
                else:
                    current_object.set_value(self.GPU.pstate_clockrange[1])
        # set pretty labels
        if value != 0:
            self.builder.get_object(f"{subsystem} Frequency Label").set_text(f"Frequency {value}(%)\nautomatic")
        else:
            self.builder.get_object(f"{subsystem} Frequency Label").set_text("Frequency (%)\nautomatic")

    def set_GPU_Percent_overclock(self, slider):
        # Run after user used the % slider on the GPU
        self.set_percent_overclock(slider,"GPU")
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_MEM_Percent_overclock(self, slider):
        # Run after user used the % slider on the MEM
        self.set_percent_overclock(slider, "MEM")
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_POW_slider(self, slider):
        # Run after user used the % slider on the power slider
        value = int(slider.get_value())
        slider.set_value(value)
        self.builder.get_object("Powerlimit Label").set_text("Power limit %d(W)\nManual" % value)
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_voltage_switch(self, switch, value, subsystem):
        if subsystem == "GPU":
            loopvariable = self.GPU.pstate_voltage
            prefix = ""
        elif subsystem == "MEM":
            loopvariable = self.GPU.pmem_voltage
            prefix="M"
        if value:
            self.builder.get_object(f"{subsystem} Voltage Label").set_text("Voltage Control (mV)\nmanual")
            [self.builder.get_object(f"{prefix}Pstate voltage {i}").set_text(str(voltage)) for i,voltage in enumerate(loopvariable)]
        else:
            self.builder.get_object(f"{subsystem} Voltage Label").set_text("Voltage Control (mV)\nautomatic")
            [self.builder.get_object(f"{prefix}Pstate voltage {i}").set_text("auto") for i,_ in enumerate(loopvariable)]
        for i,_ in enumerate(loopvariable):
            self.builder.get_object(f"{prefix}Pstate voltage {i}").set_sensitive(value)
        switch.set_state(value)

    def set_GPU_Voltage_Switch(self, switch, value):
        subsystem = "GPU"
        self.set_voltage_switch(switch,value,subsystem)
        # Run after user switches the voltage switch on the GPU side
        if self.builder.get_object("MEM Voltage auto switch").get_state() != value:
            self.set_MEM_Voltage_Switch(self.builder.get_object("MEM Voltage auto switch"),value)
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_MEM_Voltage_Switch(self, switch, value):
        # Run after user switches the voltage switch on the MEM side
        self.set_voltage_switch(switch, value, "MEM")
        if self.builder.get_object("GPU Voltage auto switch").get_state() != value:
            self.set_GPU_Voltage_Switch(self.builder.get_object("GPU Voltage auto switch"),value)
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_frequency_switch(self, switch, value, subsystem):
        if subsystem == "GPU":
            loopvariable = self.GPU.pstate_clock
        elif subsystem == "MEM":
            loopvariable = self.GPU.pmem_clock
        if value:
            for i,_ in enumerate(loopvariable):
                self.builder.get_object(f"{subsystem} manual state {i}").show()
                self.builder.get_object(f"{subsystem} state {i}").set_sensitive(value)
            self.builder.get_object(f"{subsystem} Target").hide()
            self.builder.get_object(f"{subsystem} Frequency Label").set_text("Frequency (MHz)\ndynamic")
        else:
            for i,_ in enumerate(loopvariable):
                self.builder.get_object(f"{subsystem} manual state %i" %i).hide()
                self.builder.get_object(f"{subsystem} state %i" %i).set_sensitive(value)
            target = self.builder.get_object(f"{subsystem} Target")
            target.set_value(int(0))
            target.show()
            self.set_percent_overclock(target,subsystem)
            self.builder.get_object(f"{subsystem} Frequency Label").set_text("Frequency (%)\nautomatic")
        switch.set_state(value)
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_GPU_Frequency_Switch(self, switch, value):
        # Run after user switches the frequency switch on the GPU side
        self.set_frequency_switch(switch, value, "GPU")

    def set_MEM_Frequency_Switch(self, switch, value):
        # Run after user switches the frequency switch on the MEM side
        self.set_frequency_switch(switch, value, "MEM")

    def set_Powerlimit_Switch(self, switch, value):
        # Run after user switches the power switch on the powerlimit
        self.builder.get_object("Pow Target").set_sensitive(value)
        target = int(self.builder.get_object("Pow Target").get_value())
        if value:
            self.builder.get_object("Powerlimit Label").set_text(f"Power limit {target} (W)\nmanual")
        else:
            self.builder.get_object("Powerlimit Label").set_text(f"Power limit {self.GPU.power_cap} (W)\nautomatic")
            self.builder.get_object("Pow Target").set_value(self.GPU.power_cap)
        switch.set_state(value)
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def set_FAN_Switch(self, switch, value):
        if value:
            self.builder.get_object("FAN Speed label").set_text("Speed (RPM) \nmanual")
            text = [str(self.GPU.fan_target_min[0]), str(self.GPU.fan_target[0])]
            for i in range(2):
                self.builder.get_object(f"FAN manual state {i}").set_sensitive(True)
                self.builder.get_object(f"FAN {i}").set_sensitive(True)
                self.builder.get_object(f"FAN manual state {i}").set_text(text[i])
        else:
            self.builder.get_object("FAN Speed label").set_text("Speed (RPM) \nautomatic")
            for i in range(2):
                self.builder.get_object(f"FAN manual state {i}").set_sensitive(False)
                self.builder.get_object(f"FAN {i}").set_sensitive(False)
                self.builder.get_object(f"FAN manual state {i}").set_text("auto")
                self.builder.get_object("FAN RPM Min").set_value(self.GPU.fan_target_min[0])
                self.builder.get_object("FAN RPM Target").set_value(self.GPU.fan_target[0])
        switch.set_state(value)
        self.builder.get_object("Revert").set_visible(self.check_change())
        self.builder.get_object("Apply").set_visible(self.check_change())

    def process_Edit(self, entry):
        # run after each textbox is edited
        try:
            value = int(entry.get_text())
            id = Gtk.Buildable.get_name(entry)
            system = id[:4].rstrip()
            state = int(id[-1])
            slider = self.builder.get_object(f"{system} state {state}")
            if "GPU" in system:
                limits = self.GPU.pstate_clockrange
            elif "MEM" in system:
                limits = self.GPU.pmem_clockrange
            elif "FAN" in system:
                limits = self.GPU.fan_target_range
            elif "TEMP" in system:
                # TODO make temp controls available
                return
            elif "voltage" in id:
                # GPU/MEM voltage
                limits = self.GPU.volt_range
            if value < limits[0]:
                value = limits[0]
            elif value > limits[1]:
                value = limits[1]
            entry.set_text(str(value))
            if slider is not None:
                slider.set_value(value)
            self.builder.get_object("Revert").set_visible(self.check_change())
            self.builder.get_object("Apply").set_visible(self.check_change())
        except ValueError:
            entry.set_text("Error")
            self.builder.get_object("Revert").set_visible(True)
            self.builder.get_object("Apply").set_visible(False)

    def check_change(self):
        self.new_state = self.create_state_dict()
        return self.init_state != self.new_state

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
        if self.new_state['manual_mode']:
            mode = "manual"
        else:
            mode = "auto"

        # Powermode
        outputfile.write(f"echo \"{mode}\" > {self.GPU.cardpath}/power_dpm_force_performance_level\n" )

        # Powercap
        if self.builder.get_object("POW auto switch").get_state():
            new_power_cap = self.builder.get_object("Pow Target").get_value() * 1000000
            outputfile.write(f"echo {new_power_cap})  > {self.GPU.sensors['power']['1']['cap']['path']} \n")

        # GPU P states
        sclocks = []
        svoltages = []
        write_new_pstates = False
        if self.builder.get_object("GPU Voltage auto switch").get_state():
            # all manual or frequency set to auto
            write_new_pstates = True
            for i, _ in enumerate(self.GPU.pstate_clock):
                sclocks.append(self.builder.get_object(f"GPU state {i}").get_value())
                svoltages.append(self.builder.get_object(f"Pstate voltage {i}").get_text())
        elif self.builder.get_object("GPU Frequency auto switch").get_state() and not self.builder.get_object("GPU Voltage auto switch").get_state():
            # voltage set to auto
            write_new_pstates = True
            for i, _ in enumerate(self.GPU.pstate_clock):
                sclocks.append(self.builder.get_object(f"GPU state {i}").get_value())
                svoltages.append(self.GPU.pstate_voltage[i])

        # MEM states
        mclocks = []
        mvoltages = []
        write_new_pmemstates = False
        if self.builder.get_object("MEM Voltage auto switch").get_state():
            # all manual or frequency set to auto
            write_new_pmemstates = True
            for i, _ in enumerate(self.GPU.pmem_clock):
                mclocks.append(self.builder.get_object(f"MEM state {i}").get_value())
                mvoltages.append(self.builder.get_object(f"MPstate voltage {i}").get_text())
        elif self.builder.get_object("MEM Frequency auto switch").get_state() and not self.builder.get_object("MEM Voltage auto switch").get_state():
            # voltage set to auto
            write_new_pmemstates = True
            for i, _ in enumerate(self.GPU.pmem_clock):
                mclocks.append(self.builder.get_object("MEM state " + str(i)).get_value())
                mvoltages.append(self.GPU.pmem_voltage[i])

        if write_new_pstates:
            for i, clock, voltage in zip(range(len(self.GPU.pstate_clock)), sclocks, svoltages):
                #   "s state clock voltage"
                # echo "s 0 300 750" > /sys/class/drm/card0/device/pp_od_clk_voltage
                outputfile.write(f"echo \"s {i} {clock} {voltage}\" > {self.GPU.cardpath}/pp_od_clk_voltage \n")

        if write_new_pmemstates:
            for i, clock, voltage in zip(range(len(self.GPU.pmem_clock)), mclocks, mvoltages):
                #   "m state clock voltage"
                # echo "m 0 300 750" > /sys/class/drm/card0/device/pp_od_clk_voltage
                outputfile.write(f"echo \"m {i} {clock} {voltage}\" > {self.GPU.cardpath}/pp_od_clk_voltage \n")

        if write_new_pstates or write_new_pmemstates:
            outputfile.write(f"echo \"c\" > {self.GPU.cardpath}/pp_od_clk_voltage\n")

        # GPU % overclock
        SCLK_OD = int(self.builder.get_object("GPU Target").get_value())
        if not self.builder.get_object("GPU Frequency auto switch").get_state() and (SCLK_OD != self.GPU.read_sensor("pp_sclk_od")):
            outputfile.write(f"echo {SCLK_OD} > {self.GPU.cardpath}/pp_sclk_od\n")

        # MEM % overclock
        MCLK_OD = int(self.builder.get_object("MEM Target").get_value())
        if not self.builder.get_object("MEM Frequency auto switch").get_state() and (MCLK_OD != self.GPU.read_sensor("pp_mclk_od")):
            outputfile.write(f"echo {MCLK_OD} > {self.GPU.cardpath}/pp_mclk_od\n")

        # Fan mode
        Fan_mode = "manual" if self.builder.get_object("FAN auto switch").get_state() else "auto"
        if Fan_mode == "auto" and not all(self.GPU.fan_control_value[:] == 2):
            [outputfile.write(f"echo 2 > {self.GPU.cardpath}{self.GPU.sensors['pwm'][k]['enable']['path']}\n") for k in self.GPU.sensors['pwm'].keys()]
        elif Fan_mode == "manual" and not all(self.GPU.fan_control_value[:] == 1):
            [outputfile.write(f"echo 1 > {self.GPU.cardpath}{self.GPU.sensors['pwm'][k]['enable']['path']}\n") for k in self.GPU.sensors['pwm'].keys()]


        outputfile.close()
        exit()

    def revert(self, button):
        # On pressing revert button
        self.set_initial_values()

    def on_menu_about_clicked(self, menuitem):
        # On pressing about menu item
        self.builder.get_object("About").run()
        self.builder.get_object("About").hide()
