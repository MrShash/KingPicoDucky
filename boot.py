# KingShash HID Auto Feeder boot.py file
# Setup for hide / unhide mass storage device and custom drive renaming.
# Author - shaswatmanojjha.com (Shaswat Manoj Jha)

import board, storage, digitalio

# 1. Rename the drive from CIRCUITPY to KINGSHASH
storage.remount("/", readonly=False)
m = storage.getmount("/")
m.label = "KINGSHASH"
storage.remount("/", readonly=True)

# 2. Setup the hardware switch for Stealth Mode
button = digitalio.DigitalInOut(board.GP17)
button.switch_to_input(pull=digitalio.Pull.UP)

# 3. If the button is NOT pressed (value is True due to Pull.UP), 
# completely hide the USB drive from the target computer.
if button.value:
    storage.disable_usb_drive()