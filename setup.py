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

from setuptools import setup

setup(
    name = "WattmanGTK",
    version = "0.0.1",
    author = "Bouke Haarsma",
    author_email = "boukehaarsma23@gmail.com",
    description = ("A Wattman-like GTK3+ GUI for AMDGPU users"),
    license = "GPL",
    packages = ["WattmanGTK"],
    package_dir = {"WattmanGTK":  "WattmanGTK"},
    package_data = {
        "WattmanGTK": [
            "data/wattman.ui",
            "data/WattmanGTK.eps",
            "data/WattmanGTK.svg",
            "data/WattmanGTK-outline-type.svg",
        ]
    },
    url = "https://github.com/BoukeHaarsma23/WattmanGTK",
    project_urls = {
        "Source": "https://github.com/BoukeHaarsma23/WattmanGTK",
        "Tracker": "https://github.com/BoukeHaarsma23/WattmanGTK/issues",
    },
    install_requires = [
        'pygobject',
        'matplotlib',
        'pycairo',
    ],
    entry_points={
        "console_scripts": ["wattmanGTK=WattmanGTK.wattman:main"]
    }
)
