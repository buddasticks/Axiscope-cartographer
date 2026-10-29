# /home/klipper/klippy/extras/axiscope.py
import os
import ast
import statistics
from . import tools_calibrate
from . import toolchanger


class Axiscope:
    def __init__(self, config):
        self.printer = config.get_printer()
        self.gcode = self.printer.lookup_object('gcode')
        self.gcode_move = self.printer.load_object(config, 'gcode_move')

        # Z calibration backend:
        #   switch       -> original physical endstop workflow
        #   cartographer -> T0 touch-home + Tn touch-probe workflow
        self.z_backend = config.get('z_backend', 'switch').strip().lower()
        if self.z_backend not in ('switch', 'cartographer'):
            raise config.error("[axiscope] z_backend must be 'switch' or 'cartographer'")

        # Original switch-based config
        self.x_pos = config.getfloat('zswitch_x_pos', None)
        self.y_pos = config.getfloat('zswitch_y_pos', None)
        self.z_pos = config.getfloat('zswitch_z_pos', None)

        # Cartographer config
        # Empty means auto-detect: tries [cartographer] first, then [scanner] (old plugin).
        self.cartographer_name = config.get('cartographer_name', '').strip()
        self.probe_x = config.getfloat('probe_x_pos', None)
        self.probe_y = config.getfloat('probe_y_pos', None)
        self.reference_tool = config.getint('reference_tool', 0)
        self.touch_home_gcode = config.get('touch_home_gcode', 'CARTOGRAPHER_TOUCH_HOME')
        self.touch_probe_gcode = config.get('touch_probe_gcode', 'CARTOGRAPHER_TOUCH_PROBE')
        self.touch_repeats = config.getint('touch_repeats', 3, minval=1, maxval=20)
        # Explicit lift between re-touches. Set to 0 if CARTOGRAPHER_TOUCH_PROBE already retracts.
        self.touch_retract_z = config.getfloat('touch_retract_z', 3.0, minval=0.)
        self.touch_accuracy_command = config.get('touch_accuracy_command', 'CARTOGRAPHER_TOUCH_ACCURACY')
        # Key in the touch status holding a dict with a 'range' value. Empty = range not checked.
        self.touch_accuracy_status_key = config.get('touch_accuracy_status_key', '').strip()
        self.touch_accuracy_max_range = config.getfloat('touch_accuracy_max_range', 0.01, above=0.)
        self.require_touch_accuracy = config.getboolean('require_touch_accuracy', False)
        # Default False matches the working KTC-Easy logic: offset = tap_z - reference_z.
        self.use_current_z_offsets = config.getboolean('use_current_z_offsets', False)
        self.cartographer_reference_z = None

        self.lift_z = config.getfloat('lift_z', 1)
        self.move_speed = config.getint('move_speed', 60)
        self.z_move_speed = config.getint('z_move_speed', 10)
        self.samples = config.getint('samples', 10)

        self.pin = config.get('pin', None)
        self.config_file_path = config.get('config_file_path', None)
        # Optional and informational only. Set it (e.g. ~/printer_data/config/printer.cfg) to log the touch model z_offset.
        self.touch_model_config_file_path = config.get('touch_model_config_file_path', '').strip()

        # Load gcode_macro module for template support
        self.gcode_macro = self.printer.load_object(config, 'gcode_macro')

        # Custom gcode macros
        self.start_gcode = self.gcode_macro.load_template(config, 'start_gcode', '')
        self.before_pickup_gcode = self.gcode_macro.load_template(config, 'before_pickup_gcode', '')
        self.after_pickup_gcode = self.gcode_macro.load_template(config, 'after_pickup_gcode', '')
        self.finish_gcode = self.gcode_macro.load_template(config, 'finish_gcode', '')

        self.has_cfg_data = False
        self.probe_results = {}
        self.cartographer_touch_model_z_offset = 0.0

        # Check for tools_calibrate conflict
        if config.has_section('tools_calibrate'):
            raise config.error(
                "Cannot use [axiscope] when [tools_calibrate] is also configured. "
                "Both modules conflict with each other. "
                "Please use only one: either [axiscope] or [tools_calibrate]."
            )

        # Only build the physical-switch probe path when using the switch backend
        self.probe_multi_axis = None
        if self.z_backend == 'switch' and self.pin is not None:
            self.probe_multi_axis = tools_calibrate.PrinterProbeMultiAxis(
                config,
                tools_calibrate.ProbeEndstopWrapper(config, 'x'),
                tools_calibrate.ProbeEndstopWrapper(config, 'y'),
                tools_calibrate.ProbeEndstopWrapper(config, 'z')
            )
            query_endstops = self.printer.load_object(config, 'query_endstops')
            query_endstops.register_endstop(
                self.probe_multi_axis.mcu_probe[-1].mcu_endstop,
                "Axiscope"
            )

        self.toolchanger = self.printer.load_object(config, 'toolchanger')
        self.printer.register_event_handler("klippy:connect", self.handle_connect)

        # register gcode commands
        self.gcode.register_command(
            'MOVE_TO_ZSWITCH', self.cmd_MOVE_TO_ZSWITCH,
            desc=self.cmd_MOVE_TO_ZSWITCH_help
        )
        self.gcode.register_command(
            'PROBE_ZSWITCH', self.cmd_PROBE_ZSWITCH,
            desc=self.cmd_PROBE_ZSWITCH_help
        )
        self.gcode.register_command(
            'CALIBRATE_ALL_Z_OFFSETS', self.cmd_CALIBRATE_ALL_Z_OFFSETS,
            desc=self.cmd_CALIBRATE_ALL_Z_OFFSETS_help
        )

        self.gcode.register_command(
            'AXISCOPE_START_GCODE', self.cmd_AXISCOPE_START_GCODE,
            desc="Execute the Axiscope start G-code macro"
        )
        self.gcode.register_command(
            'AXISCOPE_BEFORE_PICKUP_GCODE', self.cmd_AXISCOPE_BEFORE_PICKUP_GCODE,
            desc="Execute the Axiscope before pickup G-code macro"
        )
        self.gcode.register_command(
            'AXISCOPE_AFTER_PICKUP_GCODE', self.cmd_AXISCOPE_AFTER_PICKUP_GCODE,
            desc="Execute the Axiscope after pickup G-code macro"
        )
        self.gcode.register_command(
            'AXISCOPE_FINISH_GCODE', self.cmd_AXISCOPE_FINISH_GCODE,
            desc="Execute the Axiscope finish G-code macro"
        )
        self.gcode.register_command(
            'AXISCOPE_SAVE_TOOL_OFFSET', self.cmd_AXISCOPE_SAVE_TOOL_OFFSET,
            desc=self.cmd_AXISCOPE_SAVE_TOOL_OFFSET_help
        )
        self.gcode.register_command(
            'AXISCOPE_SAVE_MULTIPLE_TOOL_OFFSETS',
            self.cmd_AXISCOPE_SAVE_MULTIPLE_TOOL_OFFSETS,
            desc=self.cmd_AXISCOPE_SAVE_MULTIPLE_TOOL_OFFSETS_help
        )
        self.gcode.register_command(
            'AXISCOPE_SET_ENDSTOP_POSITION', self.cmd_AXISCOPE_SET_ENDSTOP_POSITION,
            desc=self.cmd_AXISCOPE_SET_ENDSTOP_POSITION_help
        )

    # ------------------------------------------------------------------
    # Cartographer helpers
    # ------------------------------------------------------------------

    def _cartographer_object(self):
        # Returns (name, object) for the first Cartographer-type object found, or (None, None).
        names = (self.cartographer_name,) if self.cartographer_name else ('cartographer', 'scanner')
        for name in names:
            obj = self.printer.lookup_object(name, None)
            if obj is not None:
                return name, obj
        return None, None

    def _cartographer_touch_status(self):
        name, obj = self._cartographer_object()
        if obj is None:
            raise self.printer.command_error(
                'No Cartographer or Scanner object found. Set cartographer_name in [axiscope].')
        status = obj.get_status(self.printer.get_reactor().monotonic())
        touch = status.get('touch') if isinstance(status, dict) else None
        if not isinstance(touch, dict):
            raise self.printer.command_error(
                '[%s] status has no touch section. Check your Cartographer version and '
                'run CARTOGRAPHER_QUERY FIELD=touch.' % name)
        return touch

    def _check_touch_model(self, gcmd):
        # Touching without a loaded touch model gives unusable Z values.
        try:
            model = self._cartographer_touch_status().get('current_model')
        except Exception as exc:
            gcmd.respond_error(str(exc))
            return False
        if model in (None, '', 'none'):
            gcmd.respond_error(
                'Cartographer has no touch model. Run CARTOGRAPHER_TOUCH_CALIBRATE first.')
            return False
        return True

    def _read_touch_z(self, gcmd):
        # Contact Z comes only from the touch result. No toolhead-height fallback.
        value = self._cartographer_touch_status().get('last_z_result')
        if value is None:
            raise gcmd.error(
                'Cartographer touch status has no last_z_result after %s'
                % self.touch_probe_gcode)
        return float(value)

    def _retract(self, toolhead):
        # Lift between re-touches, clamped to the machine's Z maximum.
        if self.touch_retract_z <= 0:
            return
        z = toolhead.get_position()[2] + self.touch_retract_z
        limits = toolhead.get_status(self.printer.get_reactor().monotonic()).get('axis_maximum')
        z_max = getattr(limits, 'z', None)
        if z_max is not None:
            z = min(z, z_max)
        toolhead.manual_move([None, None, z], self.z_move_speed)
        toolhead.wait_moves()

    def _touch_median(self, gcmd):
        toolhead = self.printer.lookup_object('toolhead')
        values = []
        previous = None
        for i in range(self.touch_repeats):
            if i > 0:
                self._retract(toolhead)
            self.gcode.run_script_from_command(self.touch_probe_gcode)
            toolhead.wait_moves()
            value = self._read_touch_z(gcmd)
            # Identical consecutive results mean the status did not update (stale read).
            if previous is not None and value == previous:
                raise gcmd.error(
                    'Cartographer touch result did not update between touches (%.6f)'
                    % value)
            values.append(value)
            previous = value
            gcmd.respond_info('touch %d/%d: Z=%.6f' % (i + 1, self.touch_repeats, value))
        return statistics.median(values), values

    def _run_touch_accuracy_gate(self, gcmd):
        if self.z_backend != 'cartographer' or not self.touch_accuracy_command:
            return True
        gcmd.respond_info('Running %s' % self.touch_accuracy_command)
        self.gcode.run_script_from_command(self.touch_accuracy_command)
        self.printer.lookup_object('toolhead').wait_moves()

        if not self.touch_accuracy_status_key:
            msg = ('Touch accuracy range not checked: set touch_accuracy_status_key '
                   'after confirming it with CARTOGRAPHER_QUERY FIELD=touch.')
            if self.require_touch_accuracy:
                gcmd.respond_error(msg + ' (require_touch_accuracy is True, aborting)')
                return False
            gcmd.respond_info(msg)
            return True

        try:
            stats = self._cartographer_touch_status().get(self.touch_accuracy_status_key)
        except Exception as exc:
            gcmd.respond_error(str(exc))
            return False
        if not isinstance(stats, dict) or stats.get('range') is None:
            msg = ('Touch accuracy key "%s" not found or has no range in touch status.'
                   % self.touch_accuracy_status_key)
            if self.require_touch_accuracy:
                gcmd.respond_error(msg + ' Aborting.')
                return False
            gcmd.respond_info(msg)
            return True

        rng = float(stats['range'])
        if rng > self.touch_accuracy_max_range:
            gcmd.respond_error(
                'Touch accuracy range %.6f exceeds limit %.6f; aborting calibration'
                % (rng, self.touch_accuracy_max_range))
            return False
        gcmd.respond_info(
            'Touch accuracy range %.6f within limit %.6f'
            % (rng, self.touch_accuracy_max_range))
        return True

    def _active_tool_number(self, gcmd):
        if self.toolchanger.active_tool is None:
            gcmd.respond_error('No active tool selected')
            return None
        return int(self.toolchanger.active_tool.tool_number)

    # ------------------------------------------------------------------
    # Config / status
    # ------------------------------------------------------------------

    def _load_cartographer_touch_model_z_offset(self):
        if not self.touch_model_config_file_path or not os.path.exists(self.touch_model_config_file_path):
            return 0.0

        section_prefixes = (
            '#*# [cartographer touch_model ',
            '#*# [scanner touch_model ',
        )
        in_touch_model = False

        try:
            with open(self.touch_model_config_file_path, 'r') as f:
                for raw_line in f:
                    line = raw_line.strip()
                    if any(line.startswith(prefix) for prefix in section_prefixes):
                        in_touch_model = True
                        continue
                    if in_touch_model and line.startswith('#*# ['):
                        in_touch_model = False
                    if in_touch_model and line.startswith('#*# z_offset ='):
                        return float(line.split('=', 1)[1].strip())
        except Exception:
            return 0.0

        return 0.0

    def _build_probe_result(self, *, source, measured_contact_z, suggested_gcode_z_offset,
                            measured_time, z_trigger=None, z_offset=None, z_delta=None,
                            touch_model_z_offset=None, trigger_distance=None):
        return {
            'source': source,
            'measured_contact_z': measured_contact_z,
            'suggested_gcode_z_offset': suggested_gcode_z_offset,
            'touch_model_z_offset': touch_model_z_offset,
            'trigger_distance': trigger_distance,
            # legacy keys for existing UI/backends
            'z_trigger': measured_contact_z if z_trigger is None else z_trigger,
            'z_offset': suggested_gcode_z_offset if z_offset is None else z_offset,
            'z_delta': measured_contact_z if z_delta is None else z_delta,
            'last_run': measured_time,
        }

    def handle_connect(self):
        if self.config_file_path is not None:
            expanded_path = os.path.expanduser(self.config_file_path)
            self.config_file_path = expanded_path
            if os.path.exists(self.config_file_path):
                self.has_cfg_data = True
                self.gcode.respond_info(
                    "Axiscope config file found (%s)." % self.config_file_path
                )
            else:
                self.gcode.respond_info(
                    "Could not find Axiscope config file (%s)" % self.config_file_path
                )
                self.gcode.respond_info(
                    "Note: You can use ~ for home directory, "
                    "e.g., ~/printer_data/config/axiscope.offsets"
                )
        else:
            self.gcode.respond_info(
                "Axiscope is missing config file location (config_file_path). "
                "You will need to update your tool offsets manually."
            )
            self.gcode.respond_info(
                "You can set config_file_path: ~/printer_data/config/axiscope.offsets "
                "in your [axiscope] section."
            )

        if self.touch_model_config_file_path:
            self.touch_model_config_file_path = os.path.expanduser(
                self.touch_model_config_file_path)

        self.gcode.respond_info(
            "--Axiscope Loaded-- (z_backend=%s)" % self.z_backend
        )

        if self.z_backend == 'cartographer':
            self.cartographer_touch_model_z_offset = self._load_cartographer_touch_model_z_offset()
            if self.touch_model_config_file_path:
                self.gcode.respond_info(
                    "Axiscope Cartographer touch_model source (%s) z_offset = %.5f"
                    % (self.touch_model_config_file_path,
                       self.cartographer_touch_model_z_offset)
                )

    def get_status(self, eventtime):
        return {
            'probe_results': self.probe_results,
            'can_save_config': self.has_cfg_data is not False,
            'endstop_x': self.x_pos,
            'endstop_y': self.y_pos,
            'endstop_z': self.z_pos,
            'z_backend': self.z_backend,
            'probe_x': self.probe_x,
            'probe_y': self.probe_y,
            'reference_tool': self.reference_tool,
            'use_current_z_offsets': self.use_current_z_offsets,
            'cartographer_reference_z': self.cartographer_reference_z,
            'cartographer_touch_model_z_offset': self.cartographer_touch_model_z_offset,
        }

    def run_gcode(self, name, template, extra_context):
        curtime = self.printer.get_reactor().monotonic()
        context = {
            **template.create_template_context(),
            'tool': self.toolchanger.active_tool.get_status(curtime)
                    if self.toolchanger.active_tool else {},
            'toolchanger': self.toolchanger.get_status(curtime),
            'axiscope': self.get_status(curtime),
            **extra_context,
        }
        template.run_gcode_from_command(context)

    def is_homed(self):
        toolhead = self.printer.lookup_object('toolhead')
        ctime = self.printer.get_reactor().monotonic()
        homed_axes = toolhead.get_kinematics().get_status(ctime)['homed_axes']
        return all(x in homed_axes for x in 'xyz')

    def has_switch_pos(self):
        return all(x is not None for x in [self.x_pos, self.y_pos, self.z_pos])

    def has_probe_point(self):
        return all(x is not None for x in [self.probe_x, self.probe_y])

    def get_tool_object_name(self, tool_no):
        return "tool T%i" % int(tool_no)

    def get_current_tool_z_offset(self, tool_no):
        tool_obj = self.printer.lookup_object(self.get_tool_object_name(tool_no), None)
        if tool_obj is None:
            return 0.0
        curtime = self.printer.get_reactor().monotonic()
        return float(tool_obj.get_status(curtime).get('gcode_z_offset', 0.0))

    def _get_last_z_result(self):
        # Kept for the switch backend's legacy probe objects.
        curtime = self.printer.get_reactor().monotonic()
        for obj_name in ('probe', 'scanner', 'cartographer'):
            obj = self.printer.lookup_object(obj_name, None)
            if obj is None:
                continue
            if hasattr(obj, 'get_status'):
                try:
                    status = obj.get_status(curtime)
                except Exception:
                    status = None
                if isinstance(status, dict) and status.get('last_z_result') is not None:
                    return float(status['last_z_result'])
            if hasattr(obj, 'last_z_result'):
                try:
                    return float(obj.last_z_result)
                except Exception:
                    pass
        return None

    # ------------------------------------------------------------------
    # Config file writing
    # ------------------------------------------------------------------

    def update_tool_offsets(self, cfg_data, tool_name, offsets):
        axis = "xyz" if len(offsets) == 3 else "xy"
        section_name = "[%s]" % tool_name
        start = None
        end = None

        # Locate the target section's body: start index, and index of the next section header.
        for i, line in enumerate(cfg_data):
            stripped = line.strip()
            if start is None:
                if stripped == section_name:
                    start = i + 1
            elif stripped.startswith('['):
                end = i
                break
        if start is not None and end is None:
            end = len(cfg_data)

        new_section = None
        for i, a in enumerate(axis):
            offset_name = "gcode_%s_offset" % a
            offset_string = "%s: %.6f\n" % (offset_name, offsets[i])

            if start is None:
                if new_section is None:
                    new_section = ["\n", section_name + "\n"]
                new_section.append(offset_string)
                continue

            # Only search inside the target section, never the whole file.
            found = None
            for j in range(start, end):
                key = cfg_data[j].strip().split(':', 1)[0].strip()
                if key == offset_name:
                    found = j
                    break

            if found is not None:
                cfg_data[found] = offset_string
            else:
                cfg_data.insert(end, offset_string)
                end += 1

        if new_section is not None:
            new_section.append("\n")
            no_touch_index = None
            if self.config_file_path and self.config_file_path.endswith('printer.cfg'):
                for idx, line in enumerate(cfg_data):
                    if line.lstrip().startswith('#*#'):
                        no_touch_index = idx
                        break
            if no_touch_index is not None:
                cfg_data = (
                    cfg_data[:no_touch_index] + ["\n"] + new_section +
                    cfg_data[no_touch_index:]
                )
            else:
                cfg_data = cfg_data + ["\n"] + new_section

        return cfg_data

    # ------------------------------------------------------------------
    # Movement and probing
    # ------------------------------------------------------------------

    cmd_MOVE_TO_ZSWITCH_help = "Move the toolhead to the Z calibration point"

    def cmd_MOVE_TO_ZSWITCH(self, gcmd):
        if not self.is_homed():
            gcmd.respond_info('Must home first.')
            return

        toolhead = self.printer.lookup_object('toolhead')
        toolhead.wait_moves()
        current_pos = toolhead.get_position()

        if self.z_backend == 'switch':
            if not self.has_switch_pos():
                gcmd.respond_error('Z switch positions are not valid.')
                return
            gcmd.respond_info('Moving to Z switch')
            self.gcode_move.cmd_G1(self.gcode.create_gcode_command(
                "G0", "G0",
                {
                    'X': self.x_pos,
                    'Y': self.y_pos,
                    'Z': current_pos[2],
                    'F': self.move_speed * 60,
                }
            ))
            toolhead.manual_move([None, None, self.z_pos + self.lift_z], self.z_move_speed)
            return

        if not self.has_probe_point():
            gcmd.respond_error('Cartographer probe point is not valid.')
            return

        gcmd.respond_info(
            'Moving to Cartographer probe point X%.3f Y%.3f'
            % (self.probe_x, self.probe_y)
        )
        self.gcode_move.cmd_G1(self.gcode.create_gcode_command(
            "G0", "G0",
            {
                'X': self.probe_x,
                'Y': self.probe_y,
                'Z': max(current_pos[2], self.lift_z),
                'F': self.move_speed * 60,
            }
        ))

    cmd_PROBE_ZSWITCH_help = "Probe the active Z calibration backend to determine offset"

    def _probe_switch_backend(self, gcmd):
        toolhead = self.printer.lookup_object('toolhead')
        tool_no = self._active_tool_number(gcmd)
        if tool_no is None:
            return
        tool_no = str(tool_no)
        start_pos = toolhead.get_position()
        z_result = self.probe_multi_axis.run_probe(
            "z-", gcmd, speed_ratio=0.5, max_distance=10.0,
            samples=self.samples
        )[2]
        measured_time = self.printer.get_reactor().monotonic()

        if tool_no == str(self.reference_tool):
            self.probe_results[tool_no] = self._build_probe_result(
                source='switch_probe_reference',
                measured_contact_z=z_result,
                suggested_gcode_z_offset=0.0,
                measured_time=measured_time,
                z_delta=0.0,
            )
        elif str(self.reference_tool) in self.probe_results:
            z_offset = z_result - self.probe_results[str(self.reference_tool)]['z_trigger']
            self.probe_results[tool_no] = self._build_probe_result(
                source='switch_probe',
                measured_contact_z=z_result,
                suggested_gcode_z_offset=z_offset,
                measured_time=measured_time,
                z_delta=z_offset,
            )
        else:
            self.probe_results[tool_no] = self._build_probe_result(
                source='switch_probe',
                measured_contact_z=z_result,
                suggested_gcode_z_offset=None,
                measured_time=measured_time,
                z_delta=None,
            )

        toolhead.move(start_pos, self.z_move_speed)
        toolhead.set_position(start_pos)
        toolhead.wait_moves()

    def _probe_cartographer_backend(self, gcmd):
        if not self.has_probe_point():
            gcmd.respond_error('Cartographer probe point is not valid.')
            return
        if not self._check_touch_model(gcmd):
            return

        toolhead = self.printer.lookup_object('toolhead')
        tool_no = self._active_tool_number(gcmd)
        if tool_no is None:
            return
        start_pos = toolhead.get_position()
        measured_time = self.printer.get_reactor().monotonic()

        if tool_no == self.reference_tool:
            # T0 sets the Z datum: touch-home, then a touch median as the reference reading.
            gcmd.respond_info('Cartographer touch-home with T%i (Z datum)' % tool_no)
            self.gcode.run_script_from_command(self.touch_home_gcode)
            toolhead.wait_moves()
            ref_z, _ = self._touch_median(gcmd)
            self.cartographer_reference_z = ref_z
            self.probe_results[str(tool_no)] = self._build_probe_result(
                source='cartographer_touch_reference',
                measured_contact_z=ref_z,
                suggested_gcode_z_offset=0.0,
                measured_time=measured_time,
                z_delta=0.0,
                touch_model_z_offset=self.cartographer_touch_model_z_offset,
            )
            gcmd.respond_info('T%i reference contact Z=%.6f' % (tool_no, ref_z))
        else:
            if self.cartographer_reference_z is None:
                gcmd.respond_error(
                    'Reference tool T%i must be measured first.' % self.reference_tool)
                return

            gcmd.respond_info('Cartographer touch-probe with T%i' % tool_no)
            measured_z, _ = self._touch_median(gcmd)
            delta = measured_z - self.cartographer_reference_z
            current_offset = self.get_current_tool_z_offset(tool_no)
            suggested_offset = current_offset + delta if self.use_current_z_offsets else delta
            self.probe_results[str(tool_no)] = self._build_probe_result(
                source='cartographer_touch',
                measured_contact_z=measured_z,
                suggested_gcode_z_offset=suggested_offset,
                measured_time=measured_time,
                z_delta=delta,
                touch_model_z_offset=self.cartographer_touch_model_z_offset,
            )
            gcmd.respond_info(
                'T%i contact Z=%.6f delta=%.6f suggested_gcode_z_offset=%.6f'
                % (tool_no, measured_z, delta, suggested_offset))

        # Lift away from the bed before the next tool change.
        safe_return_z = max(start_pos[2], self.lift_z)
        toolhead.manual_move([None, None, safe_return_z], self.z_move_speed)
        toolhead.wait_moves()

    def cmd_PROBE_ZSWITCH(self, gcmd):
        if self.z_backend == 'switch':
            if self.probe_multi_axis is None:
                gcmd.respond_error('Switch backend selected but no pin/probe is configured.')
                return
            self._probe_switch_backend(gcmd)
            return
        self._probe_cartographer_backend(gcmd)

    cmd_CALIBRATE_ALL_Z_OFFSETS_help = "Probe the configured Z backend for each tool to determine offsets"

    def cmd_CALIBRATE_ALL_Z_OFFSETS(self, gcmd):
        if not self.is_homed():
            gcmd.respond_info('Must home first.')
            return

        self.cmd_AXISCOPE_START_GCODE(gcmd)

        if not self._run_touch_accuracy_gate(gcmd):
            return

        # Per-run reset so stale reference data can't leak into this run.
        self.probe_results = {}
        self.cartographer_reference_z = None

        if self.z_backend == 'cartographer':
            ref_offset = self.get_current_tool_z_offset(self.reference_tool)
            if abs(ref_offset) > 1e-6:
                gcmd.respond_info(
                    'Warning: T%i has gcode_z_offset %.6f. Offsets are measured as differences, '
                    'but check that T%i is set up as intended.'
                    % (self.reference_tool, ref_offset, self.reference_tool))

        ordered_tools = list(self.toolchanger.tool_numbers)
        if self.reference_tool in ordered_tools:
            ordered_tools = [self.reference_tool] + [
                t for t in ordered_tools if t != self.reference_tool
            ]

        for tool_no in ordered_tools:
            self.cmd_AXISCOPE_BEFORE_PICKUP_GCODE(gcmd)
            self.gcode.run_script_from_command('T%i' % tool_no)
            self.cmd_AXISCOPE_AFTER_PICKUP_GCODE(gcmd)
            self.gcode.run_script_from_command('MOVE_TO_ZSWITCH')
            self.gcode.run_script_from_command('PROBE_ZSWITCH SAMPLES=%i' % self.samples)

        self.gcode.run_script_from_command('T%i' % self.reference_tool)
        self.printer.lookup_object('toolhead').wait_moves()

        for tool_no in ordered_tools:
            result = self.probe_results.get(str(tool_no))
            if result is None or tool_no == self.reference_tool:
                continue
            if self.z_backend == 'cartographer':
                gcmd.respond_info(
                    'T%s measured_contact_z: %.6f | suggested_gcode_z_offset: %.6f'
                    % (tool_no, result['measured_contact_z'],
                       result['suggested_gcode_z_offset']))
            else:
                gcmd.respond_info(
                    'T%s gcode_z_offset: %.3f' % (tool_no, result['z_offset']))

        self.cmd_AXISCOPE_FINISH_GCODE(gcmd)

    # Command handlers for custom macro G-code commands
    def cmd_AXISCOPE_START_GCODE(self, gcmd):
        if self.start_gcode:
            self.run_gcode('start_gcode', self.start_gcode, {})
        else:
            gcmd.respond_info("No start_gcode configured for Axiscope")

    def cmd_AXISCOPE_BEFORE_PICKUP_GCODE(self, gcmd):
        if self.before_pickup_gcode:
            self.run_gcode('before_pickup_gcode', self.before_pickup_gcode, {})
        else:
            gcmd.respond_info("No before_pickup_gcode configured for Axiscope")

    def cmd_AXISCOPE_AFTER_PICKUP_GCODE(self, gcmd):
        if self.after_pickup_gcode:
            self.run_gcode('after_pickup_gcode', self.after_pickup_gcode, {})
        else:
            gcmd.respond_info("No after_pickup_gcode configured for Axiscope")

    def cmd_AXISCOPE_FINISH_GCODE(self, gcmd):
        if self.finish_gcode:
            self.run_gcode('finish_gcode', self.finish_gcode, {})
        else:
            gcmd.respond_info("No finish_gcode configured for Axiscope")

    cmd_AXISCOPE_SAVE_TOOL_OFFSET_help = "Save a tool offset to your axiscope config file."

    def cmd_AXISCOPE_SAVE_TOOL_OFFSET(self, gcmd):
        if self.has_cfg_data is not False:
            with open(self.config_file_path, 'r') as f:
                cfg_data = f.readlines()

            tool_name = gcmd.get('TOOL_NAME')
            offsets = ast.literal_eval(gcmd.get('OFFSETS'))
            out_data = self.update_tool_offsets(cfg_data, tool_name, offsets)
            gcmd.respond_info("Writing %s offsets." % tool_name)

            with open(self.config_file_path, 'w') as f:
                for line in out_data:
                    f.write(line)
                gcmd.respond_info("Offsets written successfully.")
        else:
            gcmd.respond_info(
                "Axiscope needs a valid config location (config_file_path) to save tool offsets."
            )

    cmd_AXISCOPE_SAVE_MULTIPLE_TOOL_OFFSETS_help = "Save multiple tool offsets to your axiscope config file."

    def cmd_AXISCOPE_SAVE_MULTIPLE_TOOL_OFFSETS(self, gcmd):
        if self.has_cfg_data is not False:
            with open(self.config_file_path, 'r') as f:
                cfg_data = f.readlines()

            tool_names = ast.literal_eval(gcmd.get('TOOLS'))
            offsets = ast.literal_eval(gcmd.get('OFFSETS'))
            out_data = cfg_data

            for i, tool_name in enumerate(tool_names):
                out_data = self.update_tool_offsets(out_data, tool_name, offsets[i])

            gcmd.respond_info("Writing offsets for %s." % ', '.join(tool_names))
            with open(self.config_file_path, 'w') as f:
                for line in out_data:
                    f.write(line)
                gcmd.respond_info("Offsets written successfully.")
        else:
            gcmd.respond_info(
                "Axiscope needs a valid config location (config_file_path) to save tool offsets."
            )

    cmd_AXISCOPE_SET_ENDSTOP_POSITION_help = "Set kinematic position for X, Y, and/or Z axes"

    def cmd_AXISCOPE_SET_ENDSTOP_POSITION(self, gcmd):
        toolhead = self.printer.lookup_object('toolhead')
        current_pos = toolhead.get_position()
        use_current = gcmd.get_int('CURRENT', 0)
        x_pos = gcmd.get_float('X', None)
        y_pos = gcmd.get_float('Y', None)
        z_pos = gcmd.get_float('Z', None)

        if use_current:
            if x_pos is None:
                x_pos = current_pos[0]
            if y_pos is None:
                y_pos = current_pos[1]
            if z_pos is None:
                z_pos = current_pos[2]

        set_axes = []
        if x_pos is not None:
            if self.z_backend == 'cartographer':
                self.probe_x = x_pos
            else:
                self.x_pos = x_pos
            set_axes.append(f"X={x_pos:.3f}")
        if y_pos is not None:
            if self.z_backend == 'cartographer':
                self.probe_y = y_pos
            else:
                self.y_pos = y_pos
            set_axes.append(f"Y={y_pos:.3f}")
        if z_pos is not None:
            self.z_pos = z_pos
            set_axes.append(f"Z={z_pos:.3f}")

        if set_axes:
            if use_current:
                gcmd.respond_info(
                    f"Set axiscope calibration positions (using current): {' '.join(set_axes)}"
                )
            else:
                gcmd.respond_info(
                    f"Set axiscope calibration positions: {' '.join(set_axes)}"
                )
        else:
            gcmd.respond_info(
                "No axes specified. Use X=, Y=, Z=, and/or CURRENT=1 parameters."
            )


def load_config(config):
    return Axiscope(config)
