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

import re # for searching in strings used to determine states
import glob                 # to get directories of cards
import os
from WattmanGTK.util import read


class GPU:
    # Object which stores GPU information
    def __init__(self, cardpath, linux_kernelmain, linux_kernelsub):
        # Can used for kernel specific workarounds
        self.linux_kernelmain = linux_kernelmain
        self.linux_kernelsub = linux_kernelsub

        self.pstate = True          # Assume card has Pstate overclocking capabilities
        self.pstate_clock = []      # P state clocks (GPU) [MHz]
        self.pstate_voltage = []    # P state voltages (GPU) [mV]
        self.pmem_clock = []        # Memory state clocks [Mhz]
        self.pmem_voltage = []      # Memory state voltages [mV]
        self.pstate_clockrange = [] # Minimum and Maximum P state clocks (GPU) [Mhz]
        self.pmem_clockrange = []   # Minimum and Maximum Memory state clocks [Mhz]
        self.volt_range = []        # Mimimum and Maximum voltage for both GPU and memory [mV]
        self.cardpath = cardpath    # starting path for card eg. /sys/class/drm/card0/device
        self.sensors = self.init_sensors()
        self.get_states()
        self.get_currents()

    def get_states(self):
        # Gets the ranges for GPU and Memory (clocks states and voltages)
        # TODO add VEGA20 support
        # Source https://cgit.freedesktop.org/~agd5f/linux/tree/drivers/gpu/drm/amd/amdgpu/amdgpu_pm.c?h=amd-staging-drm-next
        # TODO make more robust for future updates
        filename = self.cardpath + "/pp_od_clk_voltage"
        try:
            with open(filename) as origin_file:
                if "OD_SCLK:" in origin_file.readline():
                    # This will not work with VEGA 20 but will work up to Vega10
                    pattern = r"^(\d|\S{1,}):\s{1,}(\d{1,})(MHz|Mhz|mV)\s{1,}(\d{1,})(MHz|Mhz|mV)"
                    # Read GPU clocks
                    match = re.match(pattern, origin_file.readline())
                    while match is not None:
                        self.pstate_clock.append(int(match.group(2)))
                        self.pstate_voltage.append(int(match.group(4)))
                        match = re.match(pattern,origin_file.readline())
                    # Read Memory clocks
                    match = re.match(pattern,origin_file.readline())
                    while match is not None:
                        self.pmem_clock.append(int(match.group(2)))
                        self.pmem_voltage.append(int(match.group(4)))
                        match = re.match(pattern,origin_file.readline())
                    # Read limits for GPU, Memory and voltages
                    match = re.match(pattern,origin_file.readline())
                    self.pstate_clockrange.append(int(match.group(2)))
                    self.pstate_clockrange.append(int(match.group(4)))

                    match = re.match(pattern,origin_file.readline())
                    self.pmem_clockrange.append(int(match.group(2)))
                    self.pmem_clockrange.append(int(match.group(4)))

                    match = re.match(pattern,origin_file.readline())
                    self.volt_range.append(int(match.group(2)))
                    self.volt_range.append(int(match.group(4)))
                else:
                    print("Error during reading current states, WattmanGTK will not be able to continue :(")
                    print("Please check if \"cat " +filename+ "\" returns something useful")
                    raise FileNotFoundError
        except FileNotFoundError:
            print("Cannot read file pp_od_clk_voltage, trying using pp_dpm_sclk and pp_dpm_mclk")
            self.pstate = False
            with open(self.cardpath + "/pp_dpm_sclk") as origin_file:
                for i, line in enumerate(origin_file.readlines()):
                    match = re.match(r"^(\d):\s(\d.*)(Mhz|MHz)\s(\*|)$", line)
                    self.pstate_clock.append(int(match.group(2)))
            with open(self.cardpath + "/pp_dpm_mclk") as origin_file:
                for i, line in enumerate(origin_file.readlines()):
                    match = re.match(r"^(\d):\s(\d.*)(Mhz|MHz)\s(\*|)$", line)
                    self.pmem_clock.append(int(match.group(2)))

        try:
            self.power_cap_max = self.sensors['power']['1']['cap']['max']['value'] / 1000000
            self.power_cap_min = self.sensors['power']['1']['cap']['min']['value'] / 1000000
            self.power_cap = self.sensors['power']['1']['cap']['value'] / 1000000
        except KeyError:
            print("No powercap sensors")
            self.power_cap_max = 0
            self.power_cap_min = 0
            self.power_cap = None
        return self.pstate_clock, self.pstate_voltage, self.pstate_clockrange, self.pmem_clock, self.pmem_voltage, self.pmem_clockrange, self.volt_range

    def init_sensors(self):
        sensors = {}
        hwmondir = '/sys/class/hwmon/'
        # Todo get hwmon folder associated with correct pci_id
        self.hwmonpath = ''
        for i,folder in enumerate(os.listdir(hwmondir)):
            if open(hwmondir + folder + '/name').readline().rstrip() == 'amdgpu':
                self.hwmonpath = hwmondir + folder
                print('amdgpu card found in ' + self.hwmonpath + ' hwmon folder')
                break

        if self.hwmonpath == '':
            print('WattmanGTK could not find any AMDGPU sensors, program will run without displaying any sensors')
            return sensors

        pattern = r"([a-zA-Z]{1,})(\d{1,})(_([a-zA-Z]{1,})|)(_([a-zA-Z]{1,})|)"
        files = "\n".join(os.listdir(self.hwmonpath))
        for match in re.finditer(pattern,files):
            # check if sensor is empty
            subsystem, sensornumber, attribute, subattribute  = match.group(1,2,4,6)
            path = "/" + match.group(0)
            value = read(self.hwmonpath + path)
            if not subsystem in sensors:
                sensors.update({subsystem: {}})
            if not sensornumber in sensors[subsystem]:
                sensors[subsystem].update({sensornumber: {}})
            if attribute is None:
                sensors[subsystem][sensornumber].update({"value": value, "path": path})
            else:
                if not attribute in sensors[subsystem][sensornumber]:
                    sensors[subsystem][sensornumber].update({attribute: {}})
                if subattribute is None:
                    sensors[subsystem][sensornumber][attribute].update({"value": value, "path": path})
                else:
                    if not subattribute in sensors[subsystem][sensornumber][attribute]:
                        sensors[subsystem][sensornumber][attribute].update({subattribute: {}})
                    sensors[subsystem][sensornumber][attribute][subattribute].update({"value": value, "path": path})
        return sensors

    def read_sensor(self,filename):
        return read(self.cardpath+"/"+filename)

    def update_sensors(self, sensordict):
        for key, value in sensordict.items():
            if type(value) is dict:
                self.update_sensors(value)
            elif key == "value":
                sensordict["value"] = read(self.hwmonpath + sensordict["path"])
            else:
                continue

    def get_current_clock(self, filename):
        # function used to get current clock speed information
        # outputs: clockvalue, clockstate
        with open(self.cardpath+filename) as origin_file:
            for line in origin_file:
                clock = re.match(r"^(\d):\s(\d.*)Mhz\s\*$", line)
                if clock:
                    return int(clock.group(2)), int(clock.group(1))

    def get_currents(self):
        # Gets current clocks and utilisation figures for displaying in GUI
        self.gpu_clock, self.gpu_state = self.get_current_clock("/pp_dpm_sclk")
        self.gpu_clock_utilisation = self.gpu_clock / self.pstate_clock[-1]

        self.mem_clock, self.mem_state = self.get_current_clock("/pp_dpm_mclk")
        self.mem_utilisation = self.mem_clock / self.pmem_clock[-1]

        self.update_sensors(self.sensors)

        try:
            if self.sensors['fan']['1']['input']['value'] is None:
                raise KeyError
            self.fan_speed = self.sensors['fan']['1']['input']['value']
        except KeyError:
            self.fan_speed = 'N/A'

        try:
            if self.sensors['pwm']['1']['value'] is None:
                raise KeyError
            self.fan_speed_pwm = self.sensors['pwm']['1']['value']
            self.fan_speed_utilisation = self.fan_speed_pwm / self.sensors['pwm']['1']['max']['value']
        except KeyError:
            self.fan_speed_pwm = 'N/A'
            self.fan_speed_utilisation = 0

        try:
            self.temperature = self.sensors['temp']['1']['input']['value'] / 1000
            self.temperature_crit = self.sensors['temp']['1']['crit']['value'] / 1000
            self.temp_utilisation = self.temperature / self.temperature_crit
        except KeyError:
            self.temp_utilisation = 0
            self.temperature = 'N/A'
            self.temperature_crit = 'N/A'
