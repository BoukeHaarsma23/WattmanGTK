# WattmanGTK
This is a Python3 program which uses a simple GTK gui to view, monitor and in the future overclock a Radeon GPU on Linux. 
![Main screen](https://i.imgur.com/m7vXaaU.png)
## What can it do?
 * View memory and GPU P-states including voltages.
 * Ability to monitor signals from GPU sensors by means of plotting
 * Write a bash file with overclock settings
 * Multi GPU support by means of prompting user which card to edit at startup
## What can't it do?
 * Directly apply values from GUI (this will be a future addition)
 * Monitor mulitple GPU's
## Requirements
 * Linux kernel 4.17+ (Ubuntu 18.10 or newer)
 * Python3
 * Python3-matplotlib
 * Python3-gi
 * A Radeon card which uses the AMDGPU kernel driver
## Usage
The tool can be launched from the command line. Clone/Download the WattmanGTK folder and open a terminal in this folder. To start the GUI run
```
./wattman.py
```
When you want to apply the settings given in the GUI click apply, and instructions will be given on how to apply the overclock. This is at your own risk!
## Contributing & Donations
Contributions can be made in terms of:
 * Hardware debugging, please let me know if your configuration runs or not (mine is run with 4.19 and an RX480)
 * Feature additions, some TODO's are given in the files
 * Packaging of the software
 * Feedback on the code
 * Donations can be made on http://paypal.me/pools/c/89hdUKrx2Z
 * Other contributions are also possible, please let me know
