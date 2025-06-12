from util.logger import Logger
from typing import Callable
from pynput import keyboard, mouse

logger = Logger(__name__)

class VoiceRecognitionInput:
    def __init__(self):
        logger.debug("Creating keyboard/mouse listener...")
        listener_k = keyboard.Listener(
            on_press=self._handle_press, # type: ignore
            on_release=self._handle_release) # type: ignore
        listener_m = mouse.Listener(
            on_click=self._handle_click) # type: ignore

        listener_k.start()
        listener_m.start()

        self.on_start_listening: Callable[[], None]
        self.on_stop_listening: Callable[[], None]
        self.on_cancel_listening: Callable[[], None]

    def _handle_press(self, key): # type: ignore
        if key == keyboard.Key.ctrl_r:
            self.on_start_listening() # type: ignore

        if key == keyboard.Key.alt_gr:
            self.on_cancel_listening() # type: ignore

    def _handle_release(self, key): # type: ignore
        if key == keyboard.Key.ctrl_r:
            self.on_stop_listening() # type: ignore

    def _handle_click(self, a1, a2, button, isPressed): # type: ignore
        if button == mouse.Button.right:
            if isPressed:
                self.on_start_listening()
            else:
                self.on_stop_listening()
