#!/usr/bin/python3
import gi                   # required for GTK3
gi.require_version("Gtk", "3.0")
from gi.repository import GLib, Gtk
import threading            # to update UI and plot
import glob                 # to get directories of cards
import time                 # for threading
import platform             # to dermine linux version
import signal               # for sigint handling

# Custom classes
from handler import Handler # handles GUI
from plot import Plot       # handles PLOT
from GPU import GPU         # handles GPU information and subroutines

CARDPATH = "/sys/class/drm/card?/device"


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


if __name__ == "__main__":
    # Proper Sigint handling
    # https://bugzilla.gnome.org/show_bug.cgi?id=622084
    signal.signal(signal.SIGINT, signal.SIG_DFL)

    # First check linux version and pp featuremask

    linux = platform.release()
    linux_kernelmain = int(linux.split(".")[0])
    linux_kernelsub = int(linux.split(".")[1])
    if not (0xffffffff == read_featuremask()):
        print ("AMDGPU is not enabled with proper featuremask is. Is amdgpu.featuremask=0xffffffff set in the command line options?")
        exit()
    if linux_kernelmain < 4 or (linux_kernelmain > 4 and linux_kernelsub < 17):
        # kernel 4.8 has percentage od source: https://www.phoronix.com/scan.php?page=news_item&px=AMDGPU-OverDrive-Support
        # kernel 4.17 has all wattman functionality source: https://www.phoronix.com/scan.php?page=news_item&px=AMDGPU-Linux-4.17-Round-1
        # For compatibility reason for now require 4.17, will later make this available to 4.8 and newer for broader compatibility
        print("Unsupported kernel (" + linux + "), make sure you are using linux kernel 4.17 or higher. ")
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
    GPU = GPU(cards[int(cardnr)], linux_kernelmain, linux_kernelsub)

    # Initialise and present GUI
    builder = Gtk.Builder()
    builder.add_from_file("wattman.ui")

    Handler = Handler(builder,GPU)
    builder.connect_signals(Handler)

    window = builder.get_object("Wattman")
    window.present()

    # Initialise plot
    maxpoints = 25 # maximum points in plot e.g. last 100 points are plotted
    precision = 2 # precision used in rounding when calculating mean/average
    Plot = Plot(builder, GPU,maxpoints, precision, linux_kernelmain, linux_kernelsub)

    # Start update thread
    refreshtime = 1  # s , timeout used inbetween updates e.g. 1Hz refreshrate on values/plot
    thread = threading.Thread(target=refresh,args=[refreshtime, Handler, Plot])
    thread.daemon = True
    thread.start()

    # Launch application
    Gtk.main()
