import gi                   # required for GTK3
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk
import threading            # to update UI and plot
import glob                 # to get directories of cards
import time                 # for threading
import platform             # to dermine linux version
import signal               # for sigint handling
from pathlib import Path

# Custom classes
from WattmanGTK.handler import Handler # handles GUI
from WattmanGTK.plot import Plot       # handles PLOT
from WattmanGTK.GPU import GPU         # handles GPU information and subroutines

CARDPATH = "/sys/class/drm/card?/device"
ROOT = Path(__file__).parent

def get_data_path(path):
    return str(ROOT.joinpath('data').joinpath(path))

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

    PP_SCLK_DPM_MASK = bool(featuremask & 0x1)
    PP_MCLK_DPM_MASK = bool(featuremask & 0x2)
    PP_PCIE_DPM_MASK = bool(featuremask & 0x4)
    PP_SCLK_DEEP_SLEEP_MASK = bool(featuremask & 0x8)
    PP_POWER_CONTAINMENT_MASK = bool(featuremask & 0x10)
    PP_UVD_HANDSHAKE_MASK = bool(featuremask & 0x20)
    PP_SMC_VOLTAGE_CONTROL_MASK = bool(featuremask & 0x40)
    PP_VBI_TIME_SUPPORT_MASK = bool(featuremask & 0x80)
    PP_ULV_MASK = bool(featuremask & 0x100)
    PP_ENABLE_GFX_CG_THRU_SMU = bool(featuremask & 0x200)
    PP_CLOCK_STRETCH_MASK = bool(featuremask & 0x400)
    PP_OD_FUZZY_FAN_CONTROL_MASK = bool(featuremask & 0x800)
    PP_SOCCLK_DPM_MASK = bool(featuremask & 0x1000)
    PP_DCEFCLK_DPM_MASK = bool(featuremask & 0x2000)
    PP_OVERDRIVE_MASK = bool(featuremask & 0x4000)
    PP_GFXOFF_MASK = bool(featuremask & 0x8000)
    PP_ACG_MASK = bool(featuremask & 0x10000)
    PP_STUTTER_MODE = bool(featuremask & 0x20000)
    PP_AVFS_MASK = bool(featuremask & 0x40000)

    if not PP_OVERDRIVE_MASK:
        print ("The overdrive functionality seems not enabled on this system.")
        print ("This means WattmanGTK can not be used.")
        print ("You could force it by flipping the overdrive bit. For this system it would mean to set amdgpu.ppfeaturemask=" + hex(featuremask + int("0x4000",16)))
        #exit()
        
    if linux_kernelmain < 4 or (linux_kernelmain >= 4 and linux_kernelsub < 7):
        # kernel 4.8 has percentage od source: https://www.phoronix.com/scan.php?page=news_item&px=AMDGPU-OverDrive-Support
        # kernel 4.17 has all wattman functionality source: https://www.phoronix.com/scan.php?page=news_item&px=AMDGPU-Linux-4.17-Round-1
        print("Unsupported kernel (" + linux + "), make sure you are using linux kernel 4.8 or higher. ")
        exit()

    # Detect where GPU is located in SYSFS
    cards = glob.glob(CARDPATH)

    # TODO: make different GPU in different TABS in headerbar
    # For now: just let user pick one on command line
    if len(cards) == 1:
        cardnr = 0
    elif len(cards) > 1:
        print("Multiple cards found!")
        [print("Card [" + str(i) + "]: " + cards[i]) for i,_ in enumerate(cards)]
        while True:
            cardnr = input("Which card do you want to use Wattman-GTK for (default: 0)? [0-9] ")
            if cardnr == "":
                cardnr = 0
                break
            elif not cardnr.isdigit():
                print("Invalid input")
            elif int(cardnr) > len(cards)-1:
                print("Out of range")
            else:
                break
    elif cards is None:
        print("No cards found")
        exit()
    else:
        print("Error detecting cards")
        exit()

    # Initialise GPU
    GPU0 = GPU(cards[int(cardnr)], linux_kernelmain, linux_kernelsub)

    # Initialise and present GUI
    builder = Gtk.Builder()
    builder.add_from_file(get_data_path("wattman.ui"))

    Handler0 = Handler(builder,GPU0)
    builder.connect_signals(Handler0)

    window = builder.get_object("Wattman")
    window.present()

    # Initialise plot
    maxpoints = 25 # maximum points in plot e.g. last 100 points are plotted
    precision = 2 # precision used in rounding when calculating mean/average
    Plot0 = Plot(builder, GPU0, maxpoints, precision, linux_kernelmain, linux_kernelsub)

    # Start update thread
    refreshtime = 1  # s , timeout used inbetween updates e.g. 1Hz refreshrate on values/plot
    thread = threading.Thread(target=refresh,args=[refreshtime, Handler0, Plot0])
    thread.daemon = True
    thread.start()

    # Launch application
    Gtk.main()
