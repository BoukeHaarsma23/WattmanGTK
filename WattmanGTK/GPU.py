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
import numpy as np
import os
from WattmanGTK.util import read
from pathlib import Path

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
        self.hwmonpath = ''

    def get_states(self):
        # Gets the ranges for GPU and Memory (clocks states and voltages)
        # Source https://cgit.freedesktop.org/~agd5f/linux/tree/drivers/gpu/drm/amd/amdgpu/amdgpu_pm.c?h=amd-staging-drm-next
        filepath = self.cardpath + "/pp_od_clk_voltage"
        label_pattern = r"^([a-zA-Z_]{1,}):$"
        clock_limit_pattern = r"^(\d|\S{1,}):\s{1,}(\d{1,})(MHz|Mhz|mV)\s{1,}(\d{1,})(MHz|Mhz|mV)$"
        print("Reading clock states and limits.")
        try:
            with open(filepath) as pp_od_clk_voltage:
                # File not that large, can put all in memory
                lines = pp_od_clk_voltage.readlines()
                lines.append("\n")
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
                        print(f"{match.group(1)} limit is not recognised by WattmanGTK, maybe this hardware is not fully supported by this version")
                else:
                    raise FileNotFoundError

            if len(self.pstate_clock + self.pstate_voltage + self.pstate_clockrange + self.pmem_clock + self.pmem_voltage + self.pmem_clockrange + self.volt_range) == 0:
                raise FileNotFoundError

        except FileNotFoundError:
            print("Cannot read file pp_od_clk_voltage, trying using pp_dpm_sclk and pp_dpm_mclk")
            print("Cannot do seperate overclocking via states, only by percentage!")
            self.pstate = False
            clock_pattern = r"^(\d):\s(\d.*)(Mhz|MHz)\s(\*|)$"
            sclk_filepath = self.cardpath + "/pp_dpm_sclk"
            mclk_filepath = self.cardpath + "/pp_dpm_mclk"
            if not os.path.isfile(sclk_filepath) or not os.path.isfile(mclk_filepath):
                print(f"Also cannot find {sclk_filepath} or {mclk_filepath}")
                print("WattmanGTK will not be able to continue")
                exit()
            with open(sclk_filepath) as origin_file:
                for i, line in enumerate(origin_file.readlines()):
                    match = re.match(clock_pattern, line)
                    if match:
                        self.pstate_clock.append(int(match.group(2)))
            with open(mclk_filepath) as origin_file:
                for i, line in enumerate(origin_file.readlines()):
                    match = re.match(clock_pattern, line)
                    if match:
                        self.pmem_clock.append(int(match.group(2)))

            if len(self.pstate_clock) == 0 or len(self.pmem_clock) == 0:
                print(f"Also got an error reading {self.cardpath + '/pp_dpm_sclk'} or {self.cardpath + '/pp_dpm_sclk'}")
                print("WattmanGTK will not be able to continue")
                exit()

        try:
            self.power_cap_max = int(self.sensors['power']['1']['cap']['max']['value'] / 1000000)
            self.power_cap_min = int(self.sensors['power']['1']['cap']['min']['value'] / 1000000)
            self.power_cap = int(self.sensors['power']['1']['cap']['value'] / 1000000)
        except (KeyError, TypeError):
            print("No powercap sensors")
            self.power_cap_max = 0
            self.power_cap_min = 0
            self.power_cap = None

        try:
            self.fan_control_value = np.array([self.sensors['pwm'][k]['enable']['value'] for k in self.sensors['fan'].keys()])
            self.fan_target_min = np.array([self.sensors['fan'][k]['min']['value'] for k in self.sensors['fan'].keys()])
            self.fan_target = np.array([self.sensors['fan'][k]['target']['value'] for k in self.sensors['fan'].keys()])
            self.fan_target_range = np.array([self.sensors['fan']['1']['min']['value'], self.sensors['fan']['1']['max']['value']])
        except (KeyError, TypeError):
            print("No fan control")
            self.fan_control_value = [None]
            self.fan_target_min = [None]
            self.fan_target = [None]

        return self.pstate_clock, self.pstate_voltage, self.pstate_clockrange, self.pmem_clock, self.pmem_voltage, self.pmem_clockrange, self.volt_range

    def init_sensors(self):
        sensors = {}
        if self.hwmonpath == '':
            print("WattmanGTK could not link the hwmon folder to the proper card, program will run without displaying any sensors")
            return sensors
        pattern = r"([a-zA-Z]{1,})(\d{1,})(_([a-zA-Z]{1,})|)(_([a-zA-Z]{1,})|)"
        files = "\n".join(os.listdir(self.hwmonpath))
        for match in re.finditer(pattern,files):
            # check if sensor is empty
            print(f"Found sensor {match.group(0).rstrip()}")
            subsystem, sensornumber, attribute, subattribute  = match.group(1,2,4,6)
            path = "/" + match.group(0).rstrip()
            print(f"Trying to read {self.hwmonpath + path}")
            value = read(self.hwmonpath + path)
            if value is None:
                print(f"Cannot read {self.hwmonpath + path}")
                continue
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
                sensordict['value'] = read(self.hwmonpath + sensordict['path'])
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
        return None, None

    def get_currents(self):
        # Gets current clocks and utilisation figures for displaying in GUI
        gpu_clock, gpu_state = self.get_current_clock("/pp_dpm_sclk")
        if gpu_clock is not None:
            self.gpu_clock = gpu_clock
            self.gpu_state = gpu_state
            self.gpu_clock_utilisation = self.gpu_clock / self.pstate_clock[-1]
        else:
            self.gpu_clock = 'N/A'
            self.gpu_state = 'N/A'
            self.gpu_clock_utilisation = 0

        mem_clock, mem_state = self.get_current_clock("/pp_dpm_mclk")
        if mem_clock is not None:
            self.mem_clock = mem_clock
            self.mem_state = mem_state
            self.mem_utilisation = self.mem_clock / self.pmem_clock[-1]
        else:
            self.mem_clock = 'N/A'
            self.mem_state = 'N/A'
            self.mem_utilisation = 0

        self.update_sensors(self.sensors)

        try:
            if self.sensors['fan']['1']['input']['value'] is None:
                raise KeyError
            self.fan_speed = self.sensors['fan']['1']['input']['value']
            self.fan_speed_rpm_utilisation = self.fan_speed / self.sensors['fan']['1']['max']['value']
        except KeyError:
            self.fan_speed_rpm_utilisation = None
            self.fan_speed = 'N/A'

        try:
            if self.sensors['pwm']['1']['value'] is None:
                raise KeyError
            self.fan_speed_pwm = self.sensors['pwm']['1']['value']
            self.fan_speed_pwm_utilisation = self.fan_speed_pwm / self.sensors['pwm']['1']['max']['value']
        except (KeyError, TypeError):
            self.fan_speed_pwm = 'N/A'
            self.fan_speed_pwm_utilisation = None

        if self.fan_speed_rpm_utilisation is None and self.fan_speed_pwm_utilisation is not None:
            self.fan_speed_utilisation = self.fan_speed_pwm_utilisation
        elif self.fan_speed_rpm_utilisation is not None:
            self.fan_speed_utilisation = self.fan_speed_rpm_utilisation
        else:
            self.fan_speed_utilisation = 0

        try:
            self.temperature = self.sensors['temp']['1']['input']['value'] / 1000
            self.temperature_crit = self.sensors['temp']['1']['crit']['value'] / 1000
            self.temp_utilisation = self.temperature / self.temperature_crit
        except (KeyError, TypeError):
            self.temp_utilisation = 0
            self.temperature = 'N/A'
            self.temperature_crit = 'N/A'
        except ZeroDivisionError:
            # set 100 degree as critical temperature
            self.temp_utilisation = self.temperature / 100
