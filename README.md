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

Axiscope supports two Z calibration workflows:

### 1. Cartographer touch workflow

ONLY TESTED WITH CARTOGRAPHER V4

- Uses `CARTOGRAPHER_TOUCH_HOME` on the reference tool to set the Z datum
- Uses `CARTOGRAPHER_TOUCH_PROBE` on the remaining tools, taking several touches per tool and using the median
- Reports **Contact Z** and **Suggested Z** in the web UI
- Shows the active source as **Cartographer Touch** / **Cartographer Ref**
- Hides the original Z-endstop map, since that graphic only applies to the physical switch workflow

### 2. Original Z-switch / endstop workflow

This is the classic Axiscope method.

- Uses a physical switch mounted at a known XY/Z location
- Measures each tool against that switch
- The UI shows the Z-endstop position map and **Set Current Position** button

## Hardware Requirements

### Camera Options

#### DIY Option

The following parts are required if you want to build the camera yourself:

- [XY Nozzle Alignment Camera](https://www.printables.com/model/1099576-xy-nozzle-alignment-camera) - 3D printed parts
- OV9726 camera module
- 5V 3mm round white 6000-6500K LEDs x 4

#### Pre-assembled Option

A fully assembled camera with long USB cable can be purchased from:

- [Ember Prototypes](https://www.emberprototypes.com/products/cxc)

### Z Calibration Requirements (Optional)

If you want to use automatic Z calibration, choose one of the following:

#### For `z_backend: cartographer`

- A working Cartographer install with Survey Touch firmware
- A calibrated touch model. Run `CARTOGRAPHER_TOUCH_CALIBRATE` if `CARTOGRAPHER_QUERY FIELD=touch` shows no current model
- Working `CARTOGRAPHER_TOUCH_HOME` and `CARTOGRAPHER_TOUCH_PROBE` macros
- A bed that is level, and a nozzle that can be kept below 150 °C during touching
- A known probe point that all tools can safely reach
- A reference tool, normally `T0`

#### For `z_backend: switch`

- An endstop switch mounted at a known position
- A `pin` for the switch, and `zswitch_x_pos`, `zswitch_y_pos` and `zswitch_z_pos` in `printer.cfg`

## Installation

**Requirements:**

- Klipper installed and running
- [Klipper Tool Changer](https://github.com/viesturz/klipper-toolchanger)
- Moonraker configured
- Camera setup in Crowsnest & Mainsail
- SSH access to your printer

Quick installation using curl (stable `main` branch):

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

If you only want camera-based XY alignment, Axiscope can be installed without any Z backend. Leave out the `[axiscope]` Z options and the XY workflow still runs.

### Cartographer backend configuration

Add the following to your `printer.cfg`:

```ini
# printer.cfg

[axiscope]
# --- Backend ---
z_backend: cartographer
# Empty = auto-detect [cartographer], then [scanner] (old plugin).
cartographer_name:

# --- Probe point and tools ---
probe_x_pos: 100.0          # clear spot on the bed that every tool can reach
probe_y_pos: 100.0
reference_tool: 0           # T0 sets the Z datum

# --- Touch commands ---
touch_home_gcode: CARTOGRAPHER_TOUCH_HOME
touch_probe_gcode: CARTOGRAPHER_TOUCH_PROBE
touch_repeats: 3            # touches per tool; the median is used
touch_retract_z: 3.0        # lift between re-touches; set 0 if the touch macro already retracts
use_current_z_offsets: False  # False = offset is tap_z - reference_z

# --- Safety ---
require_zero_reference_offset: True  # abort if T0 has a non-zero gcode_z_offset

# --- Touch accuracy check ---
touch_accuracy_command: CARTOGRAPHER_TOUCH_ACCURACY
touch_accuracy_status_key:           # empty = range not checked (see below)
touch_accuracy_max_range: 0.01
require_touch_accuracy: False

# --- Motion ---
lift_z: 1
move_speed: 60
z_move_speed: 10

# --- Saving ---
# File that holds your [tool Tn] sections (usually printer.cfg).
config_file_path: ~/printer_data/config/printer.cfg
# Optional: logs the touch model z_offset at startup. Leave empty to skip.
touch_model_config_file_path:

# --- Optional macros ---
# start_gcode:
# before_pickup_gcode:
# after_pickup_gcode:
# finish_gcode:
```

### Switch backend configuration

Add the following to your `printer.cfg` if you use the physical Z switch:

```ini
# printer.cfg

[axiscope]
z_backend: switch
pin: ^PA4                    # your endstop pin
zswitch_x_pos: 226.71
zswitch_y_pos: -18.46
zswitch_z_pos: 7.8           # see "Finding the endstop position" below
samples: 10                  # switch backend only
config_file_path: ~/printer_data/config/printer.cfg

# --- Optional macros ---
# start_gcode:
# before_pickup_gcode:
# after_pickup_gcode:
# finish_gcode:
```

#### What the Cartographer options mean

- **`z_backend`**: `cartographer` selects the touch workflow. `switch` selects the physical endstop workflow.
- **`cartographer_name`**: the name of your Cartographer section. Leave it empty to auto-detect `[cartographer]`, then `[scanner]` (old plugin).
- **`probe_x_pos` / `probe_y_pos`**: the XY point on the bed where all tools are touched. Pick a spot every tool can reach safely.
- **`reference_tool`**: the tool that sets the Z datum. In most toolchanger setups this is `T0`.
- **`touch_home_gcode`**: the command that establishes the reference tool's Z zero. Normally `CARTOGRAPHER_TOUCH_HOME`.
- **`touch_probe_gcode`**: the command that touches each other tool. Normally `CARTOGRAPHER_TOUCH_PROBE`.
- **`touch_repeats`**: how many touches to take per tool. The median is used, which reduces the effect of one bad touch.
- **`touch_retract_z`**: how far to lift between repeat touches. Axiscope clamps the lift to the machine's Z maximum. Set it to `0` if `CARTOGRAPHER_TOUCH_PROBE` already retracts after each touch.
- **`use_current_z_offsets`**:
  - `False` reports `tool Z − reference Z` as the suggested `gcode_z_offset`. Use this for first-time setup and re-zeroing.
  - `True` adds that difference to the tool's current `gcode_z_offset`. Only use this if your tools are measured with their offsets already removed.
- **`require_zero_reference_offset`**: when `True`, the run stops if T0 has a non-zero `gcode_z_offset`. The touch datum has to be T0 at zero, or every other tool is shifted by the same amount. Set it to `False` only if you know your datum is correct.
- **`touch_accuracy_command`**: the command that runs the touch repeatability check before calibration. Default `CARTOGRAPHER_TOUCH_ACCURACY`.
- **`touch_accuracy_status_key`**: the touch-status key that holds the accuracy `range` value. It's empty by default, so the range is not checked and the log says so. Set it after `CARTOGRAPHER_QUERY FIELD=touch` shows the key on your Cartographer version.
- **`touch_accuracy_max_range`**: the largest accepted accuracy range in mm when the check is enabled.
- **`require_touch_accuracy`**: when `True`, the run stops if the range can't be checked or fails the limit.
- **`lift_z`**: how high the tool is lifted between measurements, in mm.
- **`move_speed`**: XY travel speed while moving to the probe point, in mm/s.
- **`z_move_speed`**: Z speed for lifts and returns, in mm/s.
- **`config_file_path`**: the file that offset save commands write to. It must be the file that holds your `[tool Tn]` sections. If that file is included by `printer.cfg`, Klipper reads it on restart.
- **`touch_model_config_file_path`**: optional. Set it (for example `~/printer_data/config/printer.cfg`) to log the saved touch model `z_offset` at startup. It is informational only and does not change any calibration result.

#### What the switch options mean

- **`pin`**: the endstop input pin. Required for the switch backend.
- **`zswitch_x_pos` / `zswitch_y_pos` / `zswitch_z_pos`**: the switch location, found as described below.
- **`samples`**: the number of probe samples per tool for the switch backend. The Cartographer backend does not use it; it uses `touch_repeats` instead.

### Recommended first Cartographer setup

For most new users:

- set `reference_tool: 0`
- leave `use_current_z_offsets: False`
- leave `require_zero_reference_offset: True`
- choose a `probe_x_pos` / `probe_y_pos` location that every tool can reach safely
- run `CARTOGRAPHER_TOUCH_ACCURACY` by hand once before your first calibration, so you know the touch repeatability

### G-code macro options

Axiscope supports templated G-code macros with full Jinja template support. The examples above leave them commented out. Add them only if your setup needs them. For example, a `start_gcode` might home the printer, select T0 and run your gantry leveling macro before any measurement.

- **start_gcode**: runs once at the beginning of calibration
- **before_pickup_gcode**: runs before each tool pickup
- **after_pickup_gcode**: runs after each tool pickup
- **finish_gcode**: runs after calibration is complete

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

#### Cartographer backend

1. Confirm the touch model: `CARTOGRAPHER_QUERY FIELD=touch` should show a `Current Model`. If it's empty, run `CARTOGRAPHER_TOUCH_CALIBRATE`.
2. Level the bed, heat the nozzle below 150 °C and home (`G28`).
3. Make sure T0 has a zero `gcode_z_offset`. Calibration stops if it doesn't (unless `require_zero_reference_offset` is `False`).
4. Run **CALIBRATE ALL Z-OFFSETS**. The run does the following:
   - runs `start_gcode`
   - runs the touch accuracy check and reports the range, if a status key is set
   - touch-homes T0 and takes the median of `touch_repeats` touches as the reference
   - touches each other tool the same way and reports the difference from T0
   - returns to T0 and runs `finish_gcode`
5. Read the console. Each tool shows its **Contact Z** and **Suggested Z**. Nothing is saved yet.
6. Save the offsets (see below).

The web UI updates **Contact Z** and **Suggested Z** for each tool. The source line shows `Cartographer Touch` or `Cartographer Ref`. The copied `gcode_z_offset` comes from the **Suggested Z** field.

#### Recalibrating one tool or only Z

A single tool can be recalibrated on its own. Select it and run `PROBE_ZSWITCH`. If the session has no T0 reference yet, Axiscope touch-homes T0 first, then returns to the tool you selected.

Z-only saves are supported. Pass `AXES=z` with a single offset, and any existing X and Y offsets in that tool's section are left unchanged.

#### Saving offsets

Use `AXISCOPE_SAVE_TOOL_OFFSET` for one tool, or `AXISCOPE_SAVE_MULTIPLE_TOOL_OFFSETS` for several. Both take:

- `OFFSETS`: `[z]` for Z only, `[x, y]` for XY, or `[x, y, z]` for all three
- `AXES`: optional. Inferred from the number of offsets if you leave it out. Use it to be explicit, e.g. `AXES=z`

Example for one tool's Z:
```
AXISCOPE_SAVE_TOOL_OFFSET TOOL_NAME="tool T1" OFFSETS=[0.05] AXES=z
```

`TOOL_NAME` must match the section header in your config exactly, for example `tool T1`. Every entry is checked before the file is written, so one bad entry writes nothing.

Axiscope writes to `config_file_path` only. Klipper reads the change on restart. Don't mix these saves with `SAVE_CONFIG` in the same run, or the two can overwrite each other.

#### Touch accuracy check

Axiscope runs `CARTOGRAPHER_TOUCH_ACCURACY` before every calibration and logs the output. The range is only enforced when `touch_accuracy_status_key` is set. When it's empty, the log says the range was not checked. Turn on `require_touch_accuracy` only after you have set the key and confirmed it works.

`PROBE_ACCURACY` checks the 2 mm trigger path, which the Z offsets don't use. It's a useful separate health check, not a required calibration step.

#### Switch backend

- Use **CALIBRATE ALL Z-OFFSETS** to probe the physical switch for all tools
- The Z-endstop map stays visible in the UI
- The map and **Set Current Position** button help set the switch location

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

### Error: T0 has a non-zero gcode_z_offset

The touch datum is T0 at zero offset. If T0 has an offset, every other tool would be shifted by the same amount, so the run stops before touching anything. Zero it with: 
```
SET_TOOL_PARAMETER T=0 PARAMETER=gcode_z_offset VALUE=0
```


Then run `SAVE_CONFIG`, and calibrate again. If you know your datum is correct, you can set `require_zero_reference_offset: False`.

### Error: Cartographer has no touch model

Run `CARTOGRAPHER_TOUCH_CALIBRATE` and make sure `CARTOGRAPHER_QUERY FIELD=touch` shows a current model before you calibrate.

### Error: Cartographer touch status has no last_z_result

Axiscope reads the contact height from the touch status after each touch. If this error appears, check that `touch_probe_gcode` is set to your working touch macro, and that the touch actually ran. The error is raised on purpose. Axiscope does not guess a Z value from the toolhead position.

### Error: touch result did not update between touches

Two consecutive touches returned the same value, which means the status didn't refresh. The run stops so that no stale value reaches your offsets. Retry the calibration. If it keeps happening, run `CARTOGRAPHER_TOUCH_ACCURACY` to check the probe.

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

