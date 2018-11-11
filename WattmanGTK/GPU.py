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

class sensor:
    def __init__(self,sensorpath):
        self.path = sensorpath

    def __len__(self): return 1

    def read(self,path=None):
        # Set optional path parameter, so it can be used as parser
        return int(open(self.path).readline().rstrip())

    def read_attribute(self,attribute,replace=False):
        return int(open(self.get_attribute_path(attribute,replace)).readline().rstrip())
    
    def get_attribute_path(self,attribute,replace=False):
        if replace:
            return str.split(self.path,"_")[0] + attribute
        return self.path + attribute

class GPU:
    # Object which stores GPU information
    def __init__(self, cardpath, linux_kernelmain, linux_kernelsub, fancyname = None):
        # Can used for kernel specific workarounds
        self.linux_kernelmain = linux_kernelmain
        self.linux_kernelsub = linux_kernelsub

        self.fancyname = fancyname  # e.g. ASUS RX480
        self.pstate = True          # Assume card has Pstate overclocking capabilities
        self.pstate_clock = []      # P state clocks (GPU) [MHz]
        self.pstate_voltage = []    # P state voltages (GPU) [mV]
        self.pmem_clock = []        # Memory state clocks [Mhz]
        self.pmem_voltage = []      # Memory state voltages [mV]
        self.pstate_clockrange = [] # Minimum and Maximum P state clocks (GPU) [Mhz]
        self.pmem_clockrange = []   # Minimum and Maximum Memory state clocks [Mhz]
        self.volt_range = []        # Mimimum and Maximum voltage for both GPU and memory [mV]
        self.cardpath = cardpath    # starting path for card eg. /sys/class/drm/card0/device
        self.fansensors, self.fanpwmsensors, self.tempsensors, self.powersensors, \
        self.voltagesensors, self.fanpwmenablesensors, self.fantargetsensors, self.fanenablesensors = self.get_sensors()
        self.get_states()
        self.get_currents()

    def get_states(self):
        # Gets the ranges for GPU and Memory (clocks states and voltages)
        # Source https://cgit.freedesktop.org/~agd5f/linux/tree/drivers/gpu/drm/amd/amdgpu/amdgpu_pm.c?h=amd-staging-drm-next
        filepath = self.cardpath + "/pp_od_clk_voltage"
        label_pattern = r"^([a-zA-Z_]{1,}):$"
        clock_limit_pattern = r"^(\d|\S{1,}):\s{1,}(\d{1,})(MHz|Mhz|mV)\s{1,}(\d{1,})(MHz|Mhz|mV)$"
        try:
            with open(filepath) as pp_od_clk_voltage:
                # File not that large, can put all in memory
                lines = pp_od_clk_voltage.readlines()

            readingSCLK = False
            readingMCLK = False
            readingVDDC = False
            readingRANGE = False
            for line, next_line in zip(lines[:-1],lines[1:]):
                labelmatch = re.match(label_pattern, next_line) is not None
                if "OD_SCLK:" in line or readingSCLK:
                    # Read GPU clocks
                    if not readingSCLK:
                        # First time entering SCLK reading, next_line should become line since first time entering line contains label
                        readingSCLK = True
                        continue
                    if labelmatch:
                        readingSCLK = False
                    match = re.match(clock_limit_pattern, line)
                    self.pstate_clock.append(int(match.group(2)))
                    self.pstate_voltage.append(int(match.group(4)))
                elif "OD_MCLK" in line or readingMCLK:
                    # Read Memory clocks
                    if not readingMCLK:
                        readingMCLK = True
                        continue
                    if labelmatch:
                        readingMCLK = False
                    match = re.match(clock_limit_pattern, line)
                    self.pmem_clock.append(int(match.group(2)))
                    self.pmem_voltage.append(int(match.group(4)))
                elif "OD_VDDC_CURVE" in line or readingVDDC:
                    print("Full VEGA20 support not implemented yet")
                    if not readingVDDC:
                        readingVDDC = True
                        continue
                    if labelmatch:
                        readingVDDC = False
                elif "OD_RANGE" in line or readingRANGE:
                    if not readingRANGE:
                        readingRANGE = True
                        continue
                    match = re.match(clock_limit_pattern,line)
                    if match is None or labelmatch:
                        readingRANGE = False
                    if "SCLK" in match.group(1):
                        self.pstate_clockrange.append(int(match.group(2)))
                        self.pstate_clockrange.append(int(match.group(4)))
                    elif "MCLK" in match.group(1):
                        self.pmem_clockrange.append(int(match.group(2)))
                        self.pmem_clockrange.append(int(match.group(4)))
                    elif "VDDC" in match.group(1):
                        self.volt_range.append(int(match.group(2)))
                        self.volt_range.append(int(match.group(4)))
                    else:
                        print(match.group(1) + "limit is not recognised by WattmanGTK, maybe this hardware is not fully supported by this version")
                else:
                    raise FileNotFoundError

        except FileNotFoundError:
            print("Cannot read file pp_od_clk_voltage, trying using pp_dpm_sclk and pp_dpm_mclk")
            self.pstate = False
            clock_pattern = r"^(\d):\s(\d.*)(Mhz|MHz)\s(\*|)$"
            sclk_filepath = self.cardpath + "/pp_dpm_sclk"
            mclk_filepath = self.cardpath + "/pp_dpm_mclk"
            if not os.path.isfile(sclk_filepath) or not os.path.isfile(mclk_filepath):
                print("Also cannot find " + sclk_filepath + " or " + mclk_filepath)
                print("WattmanGTK will not be able to continue")
                exit()
            with open(sclk_filepath) as origin_file:
                for i, line in enumerate(origin_file.readlines()):
                    match = re.match(clock_pattern, line)
                    self.pstate_clock.append(int(match.group(2)))
            with open(mclk_filepath) as origin_file:
                for i, line in enumerate(origin_file.readlines()):
                    match = re.match(clock_pattern, line)
                    self.pmem_clock.append(int(match.group(2)))

        try:
            self.power_cap_max = self.powersensors.read_attribute('_cap_max',True) / 1000000
            self.power_cap_min = self.powersensors.read_attribute('_cap_min',True) / 1000000
            self.power_cap = self.powersensors.read_attribute('_cap',True) / 1000000
        except (AttributeError, FileNotFoundError):
            print("No power sensing")
            self.power_cap_max = 0
            self.power_cap_min = 0
            self.power_cap = None
        return self.pstate_clock, self.pstate_voltage, self.pstate_clockrange, self.pmem_clock, self.pmem_voltage, self.pmem_clockrange, self.volt_range

    def get_sensors(self):
        hwmondir = '/sys/class/hwmon/'
        amdhwmonfolder = ''
        for i,folder in enumerate(os.listdir(hwmondir)):
            if open(hwmondir + folder + '/name').readline().rstrip() == 'amdgpu':
                amdhwmonfolder = hwmondir + folder
                print('amdgpu card found in ' + amdhwmonfolder + ' hwmon folder')
                break
        sensors = []
        if amdhwmonfolder == '':
            print('WattmanGTK could not find the proper HWMON folder')
            exit()
        names = ['/fan?_input','/pwm?','/temp?_input','/power?_average','in?_input','pwm?_enable','fan?_target','fan?_enable']
        for i, name in enumerate(names):
            paths = glob.glob(amdhwmonfolder + name)
            if paths == []:
                sensors.append(None)
                continue
            if len(paths) == 1:
                sensors.append(sensor(paths[0]))
            else:
                appended_sensors = []
                for path in paths:
                    appended_sensors.append(sensor(path))
                sensors.append(appended_sensors)
        return tuple(sensors)

    def read_sensor(self,filename):
        # reads sensors which only output number
        with open(self.cardpath+filename) as origin_file:
            return int(origin_file.readline())

    def read_sensor_str(self,filename):
        # reads sensor with single line string output with stripped \n
        with open(self.cardpath+filename) as origin_file:
            return origin_file.readline().rstrip()

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

        # Try getting specific sensors. If more than 1 exist, pick first one

        try:
            if len(self.fansensors) == 1:
                self.fan_speed = self.fansensors.read()
            else:
                self.fan_speed = self.fansensors[0].read()
        except (AttributeError, FileNotFoundError):
            self.fan_speed = 'N/A'

        try:
            if len(self.fanpwmsensors) == 1:
                self.fan_speed_pwm = self.fanpwmsensors.read()
            else:
                self.fan_speed_pwm = self.fanpwmsensors[0].read()
        except (AttributeError, FileNotFoundError):
            self.fan_speed_pwm = 'N/A'

        if not self.fan_speed_pwm == 'N/A':
            self.fan_speed_utilisation = self.fan_speed_pwm / 255
        else:
            self.fan_speed_utilisation = 0

        try:
            if len(self.tempsensors) == 1:
                self.temperature = self.tempsensors.read()/ 1000
                self.temperature_crit = self.tempsensors.read_attribute("_crit",True) / 1000
            else:
                self.temperature = self.tempsensors[0].read()/ 1000
                self.temperature_crit = self.tempsensors[0].read_attribute("_crit",True) / 1000
        except (AttributeError, FileNotFoundError):
            self.temperature = 'N/A'
            self.temperature_crit = 'N/A'

        if self.temperature_crit != 0 and not self.temperature_crit == 'N/A':
            self.temp_utilisation = self.temperature / self.temperature_crit
        else:
            self.temp_utilisation = 0
