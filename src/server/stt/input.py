import asyncio
from util.logger import Logger
from typing import Callable
from pynput import keyboard, mouse
import win32api
import win32con

logger = Logger(__name__)

class VoiceRecognitionInput:
    def __init__(self):
        logger.debug("Creating keyboard/mouse listener...")
        listener_k = keyboard.Listener(
            on_press=self._handle_press, # type: ignore
            on_release=self._handle_release)  # type: ignore
        listener_k.start()

        listener_m = mouse.Listener(on_click=self._handle_click)  # type: ignore
        # listener_m.start()

        self.on_start_listening: Callable[[], None]
        self.on_stop_listening: Callable[[], None]
        self.on_cancel_listening: Callable[[], None]

        self._last_mouse_right_pressed = False
        asyncio.get_event_loop().create_task(self._poll_mouse())

    async def _poll_mouse(self):
        while True:
            pressed_status = win32api.GetAsyncKeyState(win32con.VK_RBUTTON)
            is_pressed_right = pressed_status != 0
            if is_pressed_right != self._last_mouse_right_pressed:
                self._last_mouse_right_pressed = is_pressed_right

                if is_pressed_right:
                    self.on_start_listening()
                else:
                    self.on_stop_listening()

            await asyncio.sleep(1.0 / 30.0)

    def _handle_press(self, key): # type: ignore
        if key == keyboard.Key.ctrl_r:
            self.on_start_listening() # type: ignore

        if key == keyboard.Key.alt_gr:
            self.on_cancel_listening() # type: ignore

    def _handle_release(self, key): # type: ignore
        if key == keyboard.Key.ctrl_r:
            self.on_stop_listening() # type: ignore

    def _handle_click(self, a1, a2, button, isPressed): # type: ignore
        if button == mouse.Button.right and isPressed:
            self.on_start_listening()
        elif button == mouse.Button.right and not isPressed:
            self.on_stop_listening()
