import gi                   # required for GTK3
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk
import threading            # to update UI and plot
import glob                 # to get directories of cards
import time                 # for threading
import platform             # to dermine linux version
import signal               # for sigint handling
import subprocess           # for running lspci
import os
import re                   # for getting fancy GPU name
from optparse import OptionParser
from pathlib import Path

# Custom classes
from WattmanGTK.handler import Handler # handles GUI
from WattmanGTK.plot import Plot       # handles PLOT
from WattmanGTK.GPU import GPU         # handles GPU information and subroutines

ROOT = Path(__file__).parent

CARDPATH = "/sys/class/drm/card?/device"

def get_data_path(path):
    return str(ROOT.joinpath("data").joinpath(path))

def read_featuremask():
    # check featuremask to retrieve current featuremask
    with open("/sys/module/amdgpu/parameters/ppfeaturemask") as origin_file:
        return int(origin_file.readline())


def refresh(refreshtime,Handler,Plot):
    # Used in thread to update the values in the gui and plot
    while True:
        GLib.idle_add(Handler.update_gui)
        GLib.idle_add(Plot.refresh)
        time.sleep(refreshtime)


def main():
    # Proper Sigint handling
    # https://bugzilla.gnome.org/show_bug.cgi?id=622084
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    parser = OptionParser()
    parser.add_option("-o", "--override", help="override when program fails a check ", metavar="linux/overdrive", type="str")
    parser.add_option("-p", "--plotpoints", help="number of points to plot", metavar="number", default=25, type="int")
    parser.add_option("-f", "--frequency", help="frequency in Hz to refresh plot area [1-5]", metavar="number", default=1, type="int")
    parser.add_option("-r", "--rounding", help="digits to round to in plot", metavar="number", default=2, type="int")
    (options,_ ) = parser.parse_args()
    if options.override == "linux":
        print("Will not stop at linux kernel errors")
        override_linux = True
    elif options.override == "overdrive":
        print("Will not stop if ppfeaturemask has no overdrive")
        override_overdrive = True
    else:
        override_linux = False
        override_overdrive = False
    if options.frequency > 5:
        options.frequency = 5
    elif options.frequency < 1:
        options.frequency = 1

    # Check python version
    (python_major, python_minor, _) = platform.python_version_tuple()
    if python_major < "3":
        print("Please run with python3 (3.6+)")
        exit()
    elif python_major == "3" and python_minor < "6":
        print("Please use python version 3.6 and up")
        exit()

    # First check linux version and pp featuremask

    linux = platform.release()
    linux_kernelmain = int(linux.split(".")[0])
    linux_kernelsub = int(linux.split(".")[1])

    # https://github.com/torvalds/linux/blob/master/drivers/gpu/drm/amd/include/amd_shared.h#L114
    try:
        featuremask = read_featuremask()
    except FileNotFoundError:
        print("Cannot read ppfeaturemask")
        print("Assuming PP_OVERDRIVE MASK is TRUE")
        featuremask = 0x4000
        
    PP_OVERDRIVE_MASK = bool(featuremask & 0x4000)

    if not PP_OVERDRIVE_MASK:
        print ("The overdrive functionality seems not enabled on this system.")
        print ("This means WattmanGTK can not be used.")
        print ("You could force it by flipping the overdrive bit. For this system it would mean to set amdgpu.ppfeaturemask=0x%x" % (featuremask + 0x4000))
        print ("Please refer to: https://github.com/BoukeHaarsma23/WattmanGTK#FAQ on how to set this parameter")
        if not override_overdrive:
            exit()
        
    if linux_kernelmain < 4 or (linux_kernelmain >= 4 and linux_kernelsub < 7):
        # kernel 4.8 has percentage od source: https://www.phoronix.com/scan.php?page=news_item&px=AMDGPU-OverDrive-Support
        # kernel 4.17 has all wattman functionality source: https://www.phoronix.com/scan.php?page=news_item&px=AMDGPU-Linux-4.17-Round-1
        print(f"Unsupported kernel ({linux}), make sure you are using linux kernel 4.8 or higher. ")
        if not override_linux:
            exit()

    # Detect where GPU is located in SYSFS
    amd_pci_ids = subprocess.check_output("lspci | grep -E \"^.*(VGA|Display).*\[AMD\/ATI\].*$\" | grep -Eo \"^([0-9a-fA-F]+:[0-9a-fA-F]+.[0-9a-fA-F])\"", shell=True).decode().split()
    print("%s AMD GPU(s) found. Checking if correct kernel driver is used for this/these." % len(amd_pci_ids))
    GPUs = []
    for i, pci_id in enumerate(amd_pci_ids):
        lspci_info = subprocess.check_output("lspci -k -s " + pci_id, shell=True).decode().split("\n")
        if 'amdgpu' in lspci_info[2]:
            try:
                print(f"{pci_id} uses amdgpu kernel driver")
                print("Searching for sysfs path...")
                searching_sysfs_GPU = True
                sysfsdirectories = glob.glob(CARDPATH)
                for sysfsdirectory in sysfsdirectories:
                    sysfspath = str(Path(sysfsdirectory).resolve())
                    if pci_id in sysfspath[-7:]:
                        print(f"{sysfspath} belongs to {pci_id} with symbolic link to {sysfsdirectory}")
                        searching_sysfs_GPU = False
                        break
                if searching_sysfs_GPU:
                    raise AttributeError
            except (AttributeError, IndexError):
                print("Something went wrong in searching for the sysfspath")
                exit()
            print(f"Sysfs path found in {sysfspath}")
            fancyname = re.sub(r".*:\s",'',lspci_info[1])
            GPUs.append(GPU(sysfspath,linux_kernelmain,linux_kernelmain,fancyname))
        elif 'radeon' in lspci_info[2]:
            print("radeon kernel driver in use for AMD GPU at pci id %s" % pci_id)
            print("You should consider the radeon-profile project to control this card")
            exit()
        else:
            print("Something went wrong in detection of your card.")
            exit()


    hwmondir = '/sys/class/hwmon/'
    for i,folder in enumerate(os.listdir(hwmondir)):
        if open(hwmondir + folder + '/name').readline().rstrip() == 'amdgpu':
            print(f"amdgpu card found in {hwmondir}{folder} hwmon folder")
            print("Checking which device this hwmon path belongs to")
            for card in GPUs:
                if str(Path(f"{hwmondir}{folder}/device").resolve()) == card.cardpath:
                    print(f"{hwmondir}{folder} belongs to {card.cardpath} ({card.fancyname})")
                    card.hwmonpath = hwmondir + folder
                    card.sensors = card.init_sensors()
                    card.get_states()
                    break

    # Initialise and present GUI
    builder = Gtk.Builder()
    builder.add_from_file(get_data_path("wattman.ui"))

    Handler0 = Handler(builder,GPUs)
    builder.connect_signals(Handler0)

    window = builder.get_object("Wattman")
    window.present()

    # Initialise plot
    maxpoints = options.plotpoints  # maximum points in plot e.g. last 100 points are plotted
    precision = options.rounding  # precision used in rounding when calculating mean/average
    Plot0 = Handler0.init_plot(0, maxpoints, precision, linux_kernelmain, linux_kernelsub)

    # Start update thread
    refreshtime = 1 / options.frequency  # s , timeout used inbetween updates e.g. 1Hz refreshrate on values/plot
    thread = threading.Thread(target=refresh,args=[refreshtime, Handler0, Plot0])
    thread.daemon = True
    thread.start()

    # Launch application
    Gtk.main()
