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
    package_data = {"WattmanGTK": ["data/wattman.ui"]},
    url = "https://github.com/BoukeHaarsma23/WattmanGTK",
    project_urls = {
        "Source": "https://github.com/BoukeHaarsma23/WattmanGTK",
        "Tracker": "https://github.com/BoukeHaarsma23/WattmanGTK/issues",
    },
    install_requires = [
        'pygobject',
        'matplotlib',
    ],
    entry_points={
        "console_scripts": ["wattmanGTK=WattmanGTK.wattman:main"]
    }
)
