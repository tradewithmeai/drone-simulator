"""Xbox/gamepad controller support via pygame.joystick.

Provides a polling-based GamepadManager that reads analog sticks, triggers,
buttons, and D-pad with deadzone filtering and button edge detection.
Supports hot-plug connect/disconnect at runtime.
"""

import time
import pygame


class GamepadManager:
    """Manages a single gamepad/joystick with polling-based input."""

    # Xbox button indices (standard SDL mapping)
    BTN_A = 0
    BTN_B = 1
    BTN_X = 2
    BTN_Y = 3
    BTN_LB = 4
    BTN_RB = 5
    BTN_BACK = 6
    BTN_START = 7
    BTN_L3 = 8
    BTN_R3 = 9

    def __init__(self, config=None):
        config = config or {}
        self.enabled = config.get('enabled', True)
        self.deadzone = config.get('deadzone', 0.15)
        self.stick_sensitivity = config.get('stick_sensitivity', 1.0)
        self.trigger_sensitivity = config.get('trigger_sensitivity', 1.0)
        self.invert_right_y = config.get('invert_right_y', False)
        self.camera_orbit_speed = config.get('camera_orbit_speed', 2.0)
        self.camera_zoom_speed = config.get('camera_zoom_speed', 0.02)
        self.fpv_yaw_sensitivity = config.get('fpv_yaw_sensitivity', 1.0)

        self.joystick = None
        self.connected = False
        self._last_hotplug_check = 0.0
        self._hotplug_interval = 1.0

        # Current frame state
        self.left_stick = (0.0, 0.0)
        self.right_stick = (0.0, 0.0)
        self.left_trigger = 0.0
        self.right_trigger = 0.0
        self.dpad = (0, 0)
        self.buttons_pressed = {}   # rising edge this frame
        self.buttons_held = {}      # currently down
        self._prev_buttons = {}

        if self.enabled:
            self._init_joystick_subsystem()

    def _init_joystick_subsystem(self):
        """Ensure pygame joystick subsystem is initialized."""
        if not pygame.joystick.get_init():
            pygame.joystick.init()
        self._try_connect()

    def _try_connect(self):
        """Attempt to connect to the first available joystick."""
        try:
            count = pygame.joystick.get_count()
            if count > 0 and self.joystick is None:
                self.joystick = pygame.joystick.Joystick(0)
                self.joystick.init()
                self.connected = True
                name = self.joystick.get_name()
                print(f"[GAMEPAD] Connected: {name}")
        except Exception as e:
            print(f"[GAMEPAD] Connection error: {e}")
            self.joystick = None
            self.connected = False

    def _disconnect(self):
        """Handle controller disconnection."""
        if self.joystick is not None:
            try:
                self.joystick.quit()
            except Exception:
                pass
        self.joystick = None
        self.connected = False
        self._zero_state()
        print("[GAMEPAD] Disconnected")

    def _zero_state(self):
        """Reset all input state to neutral."""
        self.left_stick = (0.0, 0.0)
        self.right_stick = (0.0, 0.0)
        self.left_trigger = 0.0
        self.right_trigger = 0.0
        self.dpad = (0, 0)
        self.buttons_pressed = {}
        self.buttons_held = {}
        self._prev_buttons = {}

    def check_hotplug(self, current_time, force=False):
        """Periodically check for controller connect/disconnect."""
        if not self.enabled:
            return
        if not force and (current_time - self._last_hotplug_check) < self._hotplug_interval:
            return
        self._last_hotplug_check = current_time

        try:
            count = pygame.joystick.get_count()
        except Exception:
            return

        if self.connected and count == 0:
            self._disconnect()
        elif not self.connected and count > 0:
            self._try_connect()

    def poll(self, current_time):
        """Read all controller state. Call once per frame."""
        if not self.enabled:
            return

        self.check_hotplug(current_time)

        if not self.connected or self.joystick is None:
            return

        try:
            # Read analog sticks
            num_axes = self.joystick.get_numaxes()
            if num_axes >= 2:
                lx = self._apply_deadzone(self.joystick.get_axis(0))
                ly = self._apply_deadzone(self.joystick.get_axis(1))
                self.left_stick = (lx * self.stick_sensitivity,
                                   ly * self.stick_sensitivity)
            if num_axes >= 4:
                rx = self._apply_deadzone(self.joystick.get_axis(2))
                ry = self._apply_deadzone(self.joystick.get_axis(3))
                if self.invert_right_y:
                    ry = -ry
                self.right_stick = (rx * self.stick_sensitivity,
                                    ry * self.stick_sensitivity)

            # Read triggers (axis 4 = left, axis 5 = right)
            if num_axes >= 6:
                self.left_trigger = self._normalize_trigger(
                    self.joystick.get_axis(4)) * self.trigger_sensitivity
                self.right_trigger = self._normalize_trigger(
                    self.joystick.get_axis(5)) * self.trigger_sensitivity

            # Read D-pad (hat 0)
            if self.joystick.get_numhats() > 0:
                self.dpad = self.joystick.get_hat(0)

            # Read buttons with edge detection
            self.buttons_pressed = {}
            num_buttons = self.joystick.get_numbuttons()
            new_held = {}
            for i in range(num_buttons):
                if self.joystick.get_button(i):
                    new_held[i] = True
                    if not self._prev_buttons.get(i, False):
                        self.buttons_pressed[i] = True
            self._prev_buttons = self.buttons_held
            self.buttons_held = new_held

        except Exception:
            # Controller likely disconnected mid-read
            self._disconnect()

    def _apply_deadzone(self, value):
        """Apply deadzone with linear remapping to avoid jump artifact."""
        if abs(value) < self.deadzone:
            return 0.0
        sign = 1.0 if value > 0 else -1.0
        return sign * (abs(value) - self.deadzone) / (1.0 - self.deadzone)

    def _normalize_trigger(self, raw):
        """Convert trigger axis from -1..1 (rest at -1) to 0..1."""
        return max(0.0, (raw + 1.0) / 2.0)

    def is_connected(self):
        """Check if a controller is currently connected."""
        return self.connected
