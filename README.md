# KingPicoDucky (v2.0)

**The Ultimate Wireless HID Auto-Feeder for Raspberry Pi Pico W / Pico 2 W**

Have you ever tried to paste a massive CSV into an old school "BadUSB" or Rubber Ducky, only to watch the microcontroller crash due to memory limits, or type faster than the target computer can handle? 

**KingPicoDucky** solves this. It allows you to paste enormous text documents, CSVs, or TSV spreadsheets straight into your browser. The board then types it directly into the target USB host, properly chunked, paced, and completely wirelessly.

Maintained by **KingShash** (Shaswat Manoj Jha).

---

## 📖 Contents

- [Why KingPicoDucky?](#why-kingpicoducky)
- [✨ Core Features & Design](#-core-features--design)
- [🔥 Advanced: EDR Evasion](#-advanced-edr-evasion-stealth)
- [💻 Hardware Requirements](#-hardware-requirements)
- [🚀 Beginner's Install Guide](#-beginners-install-guide)
- [🕹️ How to Use (Web Interface)](#%EF%B8%8F-how-to-use-web-interface)
- [⚙️ Advanced Settings & Tuning](#%EF%B8%8F-advanced-settings--tuning)
- [🔌 REST API Reference](#-rest-api-reference)
- [❓ Troubleshooting](#-troubleshooting)

---

## Why KingPicoDucky?

Many Ducky-style tools excel at *short* payloads (e.g., executing a quick Powershell command). However, they break down when dealing with heavy data entry due to:

1. **Buffer limits**: Sending thousands of lines of payload all at once overflows the tiny RAM on most microcontrollers, crashing the device.
2. **Timing issues**: Traditional scripts type extremely fast. Spreadsheets or web forms often "swallow" or skip characters if they're still rendering an animation from the previous `TAB` or `ENTER`.
3. **EDR Flags**: Typing thousands of characters perfectly spaced at 10 milliseconds without moving a mouse is instantly flagged by corporate Endpoint Detection and Response (EDR) agents.

**What this tool does differently:**
The KingPicoDucky acts as an isolated Access Point. You connect to it with your phone/laptop, paste your long list of data into the sleek Apple-style web interface, and the *browser* chunks it safely. The browser sends 60 lines at a time, waits for the Pico to finish, and sends the next block.

---

## ✨ Core Features & Design

* **Premium "Glassmorphism" UI**: A state-of-the-art, dark-mode, completely offline web interface that looks incredibly futuristic and sleek.
* **Chunked "Ghost Feeder"**: The browser splits endless payload streams perfectly; you can stop and pause the feed at any time cooperatively without yanking the USB cord.
* **Smart Timing**: Wait variables explicitly for `Init`, `TAB`, `ENTER`, and general keys.
* **Live Progress**: An activity log prints out the chunks and real-time execution speeds.

---

## 🔥 Advanced: EDR Evasion & Stealth

Corporate environments now leverage advanced AI to detect "Anomalous Peripherals" and BadUSBs. Version 2.0 of KingPicoDucky provides complete mitigation against standard heuristic scans:

* **Hardware Fingerprinting**: Built into the `boot.py`, the CircuitPython `supervisor` mimics a legitimate **Dell USB Entry Keyboard** (VID: `0x413C`, PID: `0x2107`). By the time the host computer even probes the USB bus, it registers a completely mundane hardware device.
* **Behavioral Heuristics (Humanize Mode)**: Machine-perfect 10ms typing is flagged by EDRs. By checking **"Humanize typing"** in the interface, KingPicoDucky injects naturally varying delays: 
   * **20-60ms** standard typing.
   * **40-100ms** after spaces and tabs.
   * **150-400ms** longer pauses simulating human thought after punctuation and newlines.
   * **5% chance** to randomly pause and simulate a brief 'stumbling' hesitate.
* **Lack of Correlated Input**: EDRs look for keyboards that type thousands of characters with absolutely zero mouse movement. In Humanize Mode, KingPicoDucky leverages the `adafruit_hid.mouse` library to **automatically jiggle the mouse** slightly (+/- 2 pixels) at random intervals, fulfilling the "correlated input" security requirement perfectly!

---

## 💻 Hardware Requirements

1. **Raspberry Pi Pico W** or **Pico 2 W**.
2. **Micro-USB Data Cable** (charging-only cables will not work).
3. **Host Computer** (Target PC / Mac / Linux).
4. **Phone or Laptop** (to join the Pico's backend Wi-Fi terminal and control the feed).

---

## 🚀 Beginner's Install Guide

### Step 1: Flash standard CircuitPython
1. Download the [CircuitPython `.UF2` for the Pico W](https://circuitpython.org/board/raspberry_pi_pico_w/) or [Pico 2 W](https://circuitpython.org/board/raspberry_pi_pico2_w/). 
2. Unplug your Pico. **Hold down the `BOOTSEL` button** on the board, plug it into your computer, and let go of the button once the `RPI-RP2` drive appears.
3. Drag and drop the `.UF2` file onto the drive. It will reboot and reappear as a drive named `CIRCUITPY`.

### Step 2: Add essential libraries
CircuitPython needs the USB and Web Server add-ons. 
1. Download the [Adafruit CircuitPython Library Bundle](https://circuitpython.org/libraries) that matches your CircuitPython version (e.g. `9.x`).
2. Unzip it, go to the `lib` folder inside, and copy the `adafruit_hid` and `adafruit_httpserver` folders.
3. Paste both into the `lib` folder on your `CIRCUITPY` drive.

### Step 3: Copy this Project
1. Copy the `boot.py`, `code.py`, and `network.conf` files from this repository directly into the root of `CIRCUITPY`.
2. Create a folder called `static` on `CIRCUITPY`.
3. Drop `index.html`, `styles.css`, and `script.js` into that `static` folder.

### Step 4: Configure the Wi-Fi
Open `network.conf` and update the credentials for the network the Pico will *broadcast*:
```ini
ssid="KingPicoDucky"
password="Password123"
ip="192.168.4.1"
```

Save, and reset the Pico (unplug and re-plug it). 

---

## 🕹️ How to Use (Web Interface)

1. Plug the Pico into the **target** computer. 
2. On your **phone or second PC**, join the Wi-Fi network you set up in `network.conf` (`PicoDuckyNet`). 
3. Open your browser and go to `http://192.168.4.1/`. You'll see the futuristic Glassmorphism KingPicoDucky dashboard.
4. **Paste your Data**: Take a massive Excel file column or thousands of lines of text and paste it into the Payload Input.
5. **Set Delays**: If the Target PC is slow, bump the 'Tab wait' and 'Enter wait' values up to ensure it has time to process GUI changes between lines.
6. **Hit "Execute Payload"**: The tool will begin automatically typing everything seamlessly onto the Target PC! 

---

## ⚙️ Advanced Settings & Tuning

### The "Stealth" `boot.py` Switch
Included inside `boot.py` is logic to hide the USB mass-storage drive entirely from the target computer. If you have a physical switch wired between **GP17** and Ground, and the switch is OPEN, the `CIRCUITPY` drive will disappear, leaving only the "Dell Keyboard" registered. The drive will also optionally mount under the generic name `KINGSHASH` for further disguise.

### Field Delays Explained
- **Init wait**: Gives you `X` milliseconds *after* hitting execute on your phone to lean over to the Target PC and click on the specific text field/Excel cell you want the typing to start in. Minimum 2000ms recommended!
- **Tab/Enter wait**: Give the Target OS a chance to move to the next form cell or spreadsheet row before printing the next character! Set to 500ms if target OS is laggy.
- **Key delay**: Standard wait between strings of types.
- **Humanize Typing**: Dramatically increases execution time by printing char-by-char with varying gaussian-like logic, but ensures extreme EDR stealth.

---

## 🔌 REST API Reference

If you want to build automated tools to interact with your PicoDucky, here are the endpoints:

| Method | Path | Purpose |
|--------|------|---------|
| `POST` | `/execute` | Run one chunk (`{"content": "LINE\nLINE...", "humanize": false}`). |
| `POST` | `/stop` | Request cooperative abort of current run. |
| `GET` | `/status` | Returns JSON status: `busy`, `abort`. |
| `GET` | `/` | Web UI assets. |

---

## ❓ Troubleshooting

| Symptom | Solution |
|---------|----------------|
| **Can't access `http://192.168.4.1/`** | Ensure your phone/device is completely connected to the Pico's Wi-Fi. Turn off Cellular Data temporarily if your phone drops WiFi connections without internet. |
| **`ImportError` flashing on serial** | You forgot to place the `adafruit_hid` or `adafruit_httpserver` directories inside the `lib` folder of the Pico. |
| **Random letters missing during typing** | The USB Target computer is lagging behind the Pico! Increase the **Key delay** or **Tab / Enter** parameters in the UI significantly! |

---

*This project is for educational use and authorized auditing only. Unauthorized Keystroke injection is illegal.*
