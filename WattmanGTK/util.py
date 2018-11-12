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

def read(path):
    with open(path) as origin_file:
        try:
            value = origin_file.readline()
            if value == "":
                return None
            else:
                return int(value)
        except ValueError:
            return value.rstrip()
        except OSError:
            return None

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
