# WattmanGTK
This is a Python3 program which uses a simple GTK gui to view, monitor and in the future overclock a Radeon GPU on Linux. 
![Main screen](https://i.imgur.com/ahrQrEO.png)
## What can it do?
 * View memory and GPU P-states including voltages.
 * Ability to monitor signals from GPU sensors by means of plotting
 * Write a bash file with overclock settings
 * Multi GPU support in top dropdown list
## What can't it do?
 * Directly apply values from GUI (this will be a future addition)
 * Fan control (this will be a future addition)
 * Monitor multiple GPU's
## Requirements
 * Linux kernel 4.8+ (Ubuntu 16.10 or newer)
 * Python3 (3.6+)
 * Python3-matplotlib
 * Python3-gi
 * Python3-setuptools
 * Python3-cairo
 * A Radeon card which uses the AMDGPU kernel driver
 * The overdrive kernel parameter must be set.
## Usage/ installation
Clone the repository and open a terminal in this folder and install the required packages. For installation run
```
    sudo python3 setup.py install
```
After installation, the ``` wattmanGTK ``` command is available from any terminal.
Alternatively, the tool can also be launched from the command line by running
```
    python3 run.py
```
in a terminal where you cloned the repository. 
When you want to apply the settings given in the GUI click apply, and instructions will be given on how to apply the overclock. This is at your own risk!
## Contributing & Donations
Contributions can be made in terms of:
 * Hardware debugging, please let me know if your configuration runs or not (mine is run with 4.19 and an RX480)
 * Feature additions, some TODO's are given in the files
 * Packaging of the software
 * Feedback on the code
 * Donations can be made on http://paypal.me/pools/c/89hdUKrx2Z
 * Other contributions are also possible, please let me know
 ## FAQ
 ### How do I know my card has the overdrive bit enabled
 Just try to run WattmanGTK. It will tell you if your card does not 
 support overdrive. Even if this is not the case you can set a kernel 
 parameter to force overdrive to be enabled (may not work on all cards).
 For more information on how to set the parameter check the [Arch Wiki](https://wiki.archlinux.org/index.php/kernel_parameters)

 For GRUB based systems (like ubuntu): edit the /etc/default/grub file and edit the line:
```
    GRUB_CMDLINE_LINUX_DEFAULT="quiet splash"
```
And change it to:
```
    GRUB_CMDLINE_LINUX_DEFAULT="quiet splash amdgpu.ppfeaturemask=<the suggested value by WattmanGTK>"
```
Then grub needs to be updated, for ubuntu this is done by running
```
    sudo update-grub
```
For distro agnostic updating this can be done by running

on BIOS systems: ```# grub2-mkconfig -o /etc/grub2.cfg```

on UEFI systems: ```# grub2-mkconfig -o /etc/grub2-efi.cfg```

Then reboot the machine. Once rebooted you can check the current featuremask by 
```
   printf "0x%08x\n" $(cat /sys/module/amdgpu/parameters/ppfeaturemask)
```
 ### Setting the kernel parameter causes artifacts and glitching
 It could be that setting the kernelparameter can enable features that 
 should not be enabled which could be the cause.
 ### The program does not work for me
 Please open an issue here. Furthermore, refer to this thread on reddit for additional help: [link](https://www.reddit.com/r/linux/comments/9tnijg/a_gtk_wattman_like_gui_for_amd_radeon_users/)
 
 ### The program can not find a certain senor path and fails
Please refer to: https://github.com/BoukeHaarsma23/WattmanGTK/issues/1

