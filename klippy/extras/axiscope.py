import os
import ast
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

        # Cartographer probe point config
        self.probe_x = config.getfloat('probe_x_pos', None)
        self.probe_y = config.getfloat('probe_y_pos', None)
        self.reference_tool = config.getint('reference_tool', 0)
        self.touch_home_gcode = config.get('touch_home_gcode', 'CARTOGRAPHER_TOUCH_HOME')
        self.touch_probe_gcode = config.get('touch_probe_gcode', 'CARTOGRAPHER_TOUCH_PROBE')
        self.use_current_z_offsets = config.getboolean('use_current_z_offsets', True)

        self.lift_z = config.getfloat('lift_z', 1)
        self.move_speed = config.getint('move_speed', 60)
        self.z_move_speed = config.getint('z_move_speed', 10)
        self.samples = config.getint('samples', 10)

        self.pin = config.get('pin', None)
        self.config_file_path = config.get('config_file_path', None)

        # Load gcode_macro module for template support
        self.gcode_macro = self.printer.load_object(config, 'gcode_macro')

        # Custom gcode macros
        self.start_gcode = self.gcode_macro.load_template(config, 'start_gcode', '')
        self.before_pickup_gcode = self.gcode_macro.load_template(config, 'before_pickup_gcode', '')
        self.after_pickup_gcode = self.gcode_macro.load_template(config, 'after_pickup_gcode', '')
        self.finish_gcode = self.gcode_macro.load_template(config, 'finish_gcode', '')

        self.has_cfg_data = False
        self.probe_results = {}

        # Check for tools_calibrate conflict
        if config.has_section('tools_calibrate'):
            raise config.error(
                "Cannot use [axiscope] when [tools_calibrate] is also configured. "
                "Both modules conflict with each other. "
                "Please use only one: either [axiscope] or [tools_calibrate]."
            )

        # Only build the physical-switch probe path when using the switch backend
        if self.z_backend == 'switch':
            if self.pin is not None:
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
            else:
                self.probe_multi_axis = None
        else:
            self.probe_multi_axis = None

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

    def handle_connect(self):
        if self.config_file_path is not None:
            expanded_path = os.path.expanduser(self.config_file_path)
            self.config_file_path = expanded_path
            if os.path.exists(self.config_file_path):
                self.has_cfg_data = True
                self.gcode.respond_info(
                    "Axiscope config file found (%s)." % self.config_file_path
                )
                self.gcode.respond_info(
                    "--Axiscope Loaded-- (z_backend=%s)" % self.z_backend
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

    def update_tool_offsets(self, cfg_data, tool_name, offsets):
        axis = "xyz" if len(offsets) == 3 else "xy"
        section_name = "[%s]" % tool_name
        section_start = None
        section_end = None
        new_section = None

        for i, line in enumerate(cfg_data):
            stripped_line = line.lstrip()
            if stripped_line.startswith(section_name):
                section_start = i + 1
            elif section_start is not None and stripped_line.startswith('['):
                section_end = i - 1
                break

        for i, a in enumerate(axis):
            offset_name = "gcode_%s_offset" % a
            offset_value = offsets[i]
            offset_string = "%s: %.3f\n" % (offset_name, offset_value)

            if section_start is not None:
                if section_end is not None:
                    section_lines = cfg_data[section_start:section_end + 1]
                else:
                    section_lines = cfg_data[section_start:]

                found = False
                for line in section_lines:
                    stripped_line = line.lstrip()
                    if stripped_line.startswith(offset_name):
                        cfg_index = cfg_data.index(line)
                        cfg_data[cfg_index] = offset_string
                        found = True
                        break
                if not found:
                    insert_at = section_end if section_end is not None else len(cfg_data)
                    cfg_data.insert(insert_at, offset_string)
            else:
                if new_section is None:
                    new_section = ["\n", section_name + "\n"]
                new_section.append(offset_string)

        if new_section is not None:
            new_section.append("\n")
            no_touch_index = None
            if self.config_file_path.endswith('printer.cfg'):
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
        tool_no = str(self.toolchanger.active_tool.tool_number)
        start_pos = toolhead.get_position()
        z_result = self.probe_multi_axis.run_probe(
            "z-", gcmd, speed_ratio=0.5, max_distance=10.0,
            samples=self.samples
        )[2]
        measured_time = self.printer.get_reactor().monotonic()

        if tool_no == str(self.reference_tool):
            self.probe_results[tool_no] = {
                'z_trigger': z_result,
                'z_offset': 0.0,
                'z_delta': 0.0,
                'last_run': measured_time,
            }
        elif str(self.reference_tool) in self.probe_results:
            z_offset = z_result - self.probe_results[str(self.reference_tool)]['z_trigger']
            self.probe_results[tool_no] = {
                'z_trigger': z_result,
                'z_offset': z_offset,
                'z_delta': z_offset,
                'last_run': measured_time,
            }
        else:
            self.probe_results[tool_no] = {
                'z_trigger': z_result,
                'z_offset': None,
                'z_delta': None,
                'last_run': measured_time,
            }

        toolhead.move(start_pos, self.z_move_speed)
        toolhead.set_position(start_pos)
        toolhead.wait_moves()

    def _probe_cartographer_backend(self, gcmd):
        if not self.has_probe_point():
            gcmd.respond_error('Cartographer probe point is not valid.')
            return

        toolhead = self.printer.lookup_object('toolhead')
        tool_no = int(self.toolchanger.active_tool.tool_number)
        start_pos = toolhead.get_position()
        measured_time = self.printer.get_reactor().monotonic()

        if tool_no == self.reference_tool:
            gcmd.respond_info('Cartographer reference touch-home with T%i' % tool_no)
            self.gcode.run_script_from_command(self.touch_home_gcode)
            self.probe_results[str(tool_no)] = {
                'z_trigger': 0.0,
                'z_offset': 0.0,
                'z_delta': 0.0,
                'last_run': measured_time,
            }
        else:
            if str(self.reference_tool) not in self.probe_results:
                gcmd.respond_error(
                    'Reference tool T%i must be measured first.' % self.reference_tool
                )
                return

            gcmd.respond_info('Cartographer touch-probe with T%i' % tool_no)
            self.gcode.run_script_from_command(self.touch_probe_gcode)

            measured_z = self._get_last_z_result()
            if measured_z is None or abs(measured_z) < 1e-9:
                measured_z = float(toolhead.get_position()[2])

            if measured_z is None:
                raise gcmd.error(
                    'Unable to read a Cartographer touch result after %s. '
                    'Tried last_z_result and current toolhead Z.'
                    % self.touch_probe_gcode
                )

            current_offset = self.get_current_tool_z_offset(tool_no)
            suggested_offset = (
                current_offset + measured_z
                if self.use_current_z_offsets else measured_z
            )
            self.probe_results[str(tool_no)] = {
                'z_trigger': measured_z,
                'z_offset': suggested_offset,
                'z_delta': measured_z,
                'last_run': measured_time,
            }

        # lift away from the bed before the next tool change
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
            tool_key = str(tool_no)
            result = self.probe_results.get(tool_key)
            if result is None or tool_no == self.reference_tool:
                continue
            if self.z_backend == 'cartographer':
                gcmd.respond_info(
                    'T%s raw_touch_delta: %.3f | suggested_gcode_z_offset: %.3f'
                    % (tool_no, result['z_delta'], result['z_offset'])
                )
            else:
                gcmd.respond_info(
                    'T%s gcode_z_offset: %.3f'
                    % (tool_no, result['z_offset'])
                )

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

            gcmd.respond_info("Writing %s offsets." % tool_name)
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
