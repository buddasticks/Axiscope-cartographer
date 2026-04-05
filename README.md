# Axiscope

## What is Axiscope?

Axiscope is a specialized tool designed to simplify tool calibration for multi-tool 3D printers running Klipper Tool Changer Plugin using camera-assisted alignment for XY and optional backend-driven Z calibration.

It provides a streamlined interface for:

- Manual XY calibration using camera feedback
- Quick and precise T0 - Tn alignment
- Optional automatic Z calibration
- Copy-paste-ready per-tool `gcode_x_offset`, `gcode_y_offset`, and `gcode_z_offset` values

<br/>
<img src="media/axiscope.png" alt="Axiscope main UI" width="500"/><br/>

## Supported Z calibration backends

Axiscope now supports two Z calibration workflows:

### 1. Original Z-switch / endstop workflow

This is the classic Axiscope method.

- Uses a physical switch mounted at a known XY/Z location
- Measures each tool against that switch
- The UI shows the Z-endstop position map and **Set Current Position** button

### 2. Cartographer touch workflow

This is the newer backend added for Cartographer users.

- Uses `CARTOGRAPHER_TOUCH_HOME` on the reference tool
- Uses `CARTOGRAPHER_TOUCH_PROBE` on the remaining tools
- Reports **Contact Z** and **Suggested Z** in the web UI
- Shows the active source as **Cartographer Touch** / **Cartographer Ref**
- Displays the saved Cartographer touch-model `z_offset` when present
- Hides the original Z-endstop map, since that graphic only applies to the physical switch workflow

## Hardware Requirements

### Camera Options

#### DIY Option

The following parts are required if you want to build the camera yourself:

- [\[XY Nozzle Alignment Camera\]](https://www.printables.com/model/1099576-xy-nozzle-alignment-camera) - 3D printed parts
- OV9726 camera module
- 5V 3mm round white6000-6500k LEDS x 4

#### Pre-assembled Option

A fully assembled camera with long USB cable can be purchased from:
- [Ember Prototypes](https://www.emberprototypes.com/products/cxc)

### Z Calibration Requirements (Optional)

If you want to use automatic Z calibration, choose one of the following:

#### For `z_backend: switch`

- An endstop switch mounted at a known position
- Configuration added to your `printer.cfg`

#### For `z_backend: cartographer`

- A working Cartographer install
- Functional `CARTOGRAPHER_TOUCH_HOME`
- Functional `CARTOGRAPHER_TOUCH_PROBE`
- A known probe point that all tools can safely reach
- A reference tool, typically `T0`

## Installation

**Requirements:**

- Klipper installed and running
- [Klipper Tool Changer](https://github.com/viesturz/klipper-toolchanger)
- Moonraker configured
- Camera setup in Crowsnest & Mainsail
- SSH access to your printer

Quick installation using curl:

```bash
curl -sSL https://raw.githubusercontent.com/buddasticks/Axiscope-cartographer/refs/heads/main/install.sh | bash
```

The install script will:

- Create Python virtual environment
- Install required dependencies
- Set up the systemd service
- Configure Moonraker integration



### Starting Axiscope

1. Open your Mainsail interface
2. Find `axiscope` in the services list under **Klipper / Service / Host Control**
3. Use the Start/Stop button to control the service

<img style="padding-bottom: 10px;" src="media/ServiceControl.png" alt="Axiscope service control" width="250"/><br/>

## Configuration

Axiscope can be used for XY-only calibration, or for XY + Z calibration.

### XY-only

If you only want camera-based XY alignment, Axiscope can be installed without any Z backend.

### Z-switch backend configuration

If you want to use the original automatic Z calibration method with a physical switch, add the following to your `printer.cfg`:

```ini
[axiscope]
z_backend: switch
pin: !PG15                # Endstop pin
zswitch_x_pos: 226.71     # REQUIRED - X position of the endstop switch
zswitch_y_pos: -18.46     # REQUIRED - Y position of the endstop switch
zswitch_z_pos: 7.8        # REQUIRED - Z position + some clearance of the endstop switch
lift_z: 1                 # OPTIONAL - Amount to lift Z before moving (default: 1)
move_speed: 60            # OPTIONAL - XY movement speed in mm/s (default: 60)
z_move_speed: 10          # OPTIONAL - Z movement speed in mm/s (default: 10)
config_file_path: ~/printer_data/config/printer.cfg

start_gcode:
  {% set tools = printer.toolchanger.tool_numbers %}
  {% for tool in tools %}
      M104 T{tool} S150
  {% endfor %}
before_pickup_gcode: M118 pickup_gcode
after_pickup_gcode: M118 after_pickup_gcode
finish_gcode: M118 Calibration complete
  {% set tools = printer.toolchanger.tool_numbers %}
  {% for tool in tools %}
      M104 T{tool} S0
  {% endfor %}
  T0
```

### Cartographer backend configuration

If you want to use Cartographer touch probing for tool Z calibration, add something like this:

```ini
[axiscope]
z_backend: cartographer
probe_x_pos: 185
probe_y_pos: 175
reference_tool: 0
lift_z: 10
move_speed: 200
z_move_speed: 10
samples: 1
use_current_z_offsets: False
config_file_path: ~/printer_data/config/printer.cfg

touch_home_gcode: CARTOGRAPHER_TOUCH_HOME
touch_probe_gcode: CARTOGRAPHER_TOUCH_PROBE

start_gcode:
  G28
  T0
  QUAD_GANTRY_LEVEL
before_pickup_gcode:
after_pickup_gcode:
finish_gcode:
  T0
```

### Notes for Cartographer users

- `reference_tool` should normally be `0`
- Axiscope performs the reference touch-home with the reference tool first, then probes the remaining tools
- The web UI shows **Contact Z** and **Suggested Z** instead of the older `Z-Trigger` wording
- If your Cartographer setup has a saved touch-model section in the `#*#` save-config area, Axiscope reads that `z_offset` and uses it in the Cartographer fallback path when needed
- The original Z-endstop map is hidden when the Cartographer backend is active

### Finding the endstop position for the switch backend

To correctly configure the endstop position for the original Z-switch calibration:

1. Home your printer with T0 selected
2. Using the jog controls in your printer interface, carefully position the nozzle directly centered over the endstop pin
3. Note the current X, Y, and Z positions displayed in your interface
4. Use these values for `zswitch_x_pos` and `zswitch_y_pos` in your configuration
5. For `zswitch_z_pos`, add 3mm to your current Z position (if using multiple hotends of varying lengths, add additional clearance as needed)

Example: if your position readings are `X:226.71`, `Y:-18.46`, `Z:4.8`, then configure:

```ini
zswitch_x_pos: 226.71
zswitch_y_pos: -18.46
zswitch_z_pos: 7.8  # 4.8 + 3mm clearance
```

### G-code macro options

Axiscope supports templated G-code macros with full Jinja template support.

- **start_gcode**: executed at the beginning of calibration
- **before_pickup_gcode**: executed before each tool change
- **after_pickup_gcode**: executed after each tool change
- **finish_gcode**: executed after calibration is complete

### Hostname support in Moonraker

If you plan on using a hostname to connect to your printer, for example `voron.local:3000`, you will need to add the following to your `moonraker.conf`: `*.local:*`

That should look like this:

```ini
[authorization]
trusted_clients:
    192.168.0.0/16
    10.0.0.0/8
    127.0.0.0/8
    169.254.0.0/16
    172.16.0.0/12
    192.168.0.0/16
    FE80::/10
    ::1/128
cors_domains:
    *.lan
    *.local
    *.local:*
    *://localhost
    *://localhost:*
    *://my.mainsail.xyz
    *://app.fluidd.xyz
```

## Usage Guide

### Initial setup

1. Access the web interface at `http://your-printer-ip:3000`
2. Select the printer address you are trying to calibrate
3. Select the camera to use
4. Align `T0` perfectly center to the crosshair
5. Capture Position
6. Change to `Tn`
7. Re-align to center and press X and Y in the side navigator
8. Copy the new calculated offset values

<img style="padding-bottom: 10px;" src="media/T0-Aligment.gif" alt="T0 alignment" width="500"/><br/>
<img style="padding-bottom: 10px;" src="media/CapturePosChangeT1.gif" alt="Capture position and change tool" width="500"/><br/>
<img style="padding-bottom: 10px;" src="media/GrabOffset.gif" alt="Grab offset" width="500"/><br/>

### Z calibration usage

#### Switch backend

- Use **CALIBRATE ALL Z-OFFSETS** to probe the physical switch for all tools
- The Z-endstop map stays visible in the UI
- The map and **Set Current Position** button help set the switch location

#### Cartographer backend

- Use **CALIBRATE ALL Z-OFFSETS** to run the Cartographer touch workflow
- The UI will update **Contact Z** and **Suggested Z** for each tool
- The source line will show `Cartographer Touch` or `Cartographer Ref`
- The copied `gcode_z_offset` comes from the **Suggested Z** field

## Troubleshooting And FAQ

### Camera is not shown in Axiscope

The camera needs to be configured and also configured in Mainsail.
These links will guide you through installing and configuring the camera in Crowsnest and Mainsail:

[https://mellow.klipper.cn/en/docs/DebugDoc/BasicTutorial/camera/](https://mellow.klipper.cn/en/docs/DebugDoc/BasicTutorial/camera/)

[Configuring the camera in Mainsail](https://docs.mainsail.xyz/overview/settings/webcams)

### Camera only loads if it was plugged in before rebooting the printer

Some cameras will not be auto-detected by Crowsnest automatically. You can simply restart Crowsnest instead of rebooting the printer.

### Error: Duplicate chip name `probe_multi_axis`

If you encounter this error when starting Klipper:

<img src="media/duplicate_chip_error.png" alt="Duplicate chip name error" width="600"/><br/>

**Problem:** You likely have both the toolchanger's `calibrate_offsets.cfg` and Axiscope configured in your `printer.cfg`. Both modules use the same `probe_multi_axis` chip name.

**Solution:**
1. Remove or comment out the inclusion of `calibrate_offsets.cfg` in your `printer.cfg`
2. Or ensure you're only using one of these two calibration methods, not both

Only Axiscope should be using the `probe_multi_axis` module when configured correctly.

### Why does the Z-endstop map disappear when I enable Cartographer?

That is intentional.

The map and the **Set Current Position** control describe the original physical Z-switch workflow. They are hidden when `z_backend: cartographer` is active because they do not apply to the Cartographer touch workflow.

### Is the Cartographer UI backward compatible with the original Axiscope Z-endstop method?

Yes.

- The switch backend still works as before
- The Z-endstop map still appears for `z_backend: switch`
- The backend still publishes legacy `z_trigger` and `z_offset` keys for compatibility
- The UI now prefers the richer `measured_contact_z` / `suggested_gcode_z_offset` fields when available

## Credits

[Nic335](https://github.com/nic335) and [N3MI-DG](https://github.com/N3MI-DG)

## License

MIT License

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
