from pynput import keyboard
from pynput.keyboard import Key, KeyCode, Listener
from typing import Callable, Optional
import threading


class HotkeyManager:
    def __init__(self):
        self.callbacks = {}
        self.active = False
        self.listener = None
        self.current_keys = set()
    
    def register_hotkey(self, hotkey: str, callback: Callable, suppress: bool = True):
        # Convert hotkey string to key combination
        keys = self._parse_hotkey(hotkey)
        self.callbacks[hotkey] = {
            'keys': keys,
            'callback': callback,
            'suppress': suppress
        }
    
    def _parse_hotkey(self, hotkey: str) -> set:
        keys = set()
        parts = hotkey.lower().split('+')
        
        for part in parts:
            part = part.strip()
            if part == 'cmd':
                keys.add(Key.cmd)
            elif part == 'ctrl':
                keys.add(Key.ctrl)
            elif part == 'shift':
                keys.add(Key.shift)
            elif part == 'alt':
                keys.add(Key.alt)
            elif len(part) == 1:
                keys.add(KeyCode.from_char(part))
            else:
                # Handle special keys like 'space', 'enter', etc.
                special_keys = {
                    'space': Key.space,
                    'enter': Key.enter,
                    'tab': Key.tab,
                    'esc': Key.esc,
                    'escape': Key.esc
                }
                if part in special_keys:
                    keys.add(special_keys[part])
                else:
                    # Try to parse as number
                    try:
                        keys.add(KeyCode.from_char(part))
                    except:
                        pass
        
        return keys
    
    def unregister_hotkey(self, hotkey: str):
        if hotkey in self.callbacks:
            del self.callbacks[hotkey]
    
    def _on_press(self, key):
        self.current_keys.add(key)
        
        # Check if any registered hotkey matches
        for hotkey, config in self.callbacks.items():
            if config['keys'].issubset(self.current_keys):
                try:
                    config['callback']()
                except Exception as e:
                    print(f"Error executing hotkey callback: {e}")
    
    def _on_release(self, key):
        try:
            self.current_keys.discard(key)
        except KeyError:
            pass
    
    def start_listening(self):
        if not self.active:
            self.active = True
            self.listener = Listener(on_press=self._on_press, on_release=self._on_release)
            self.listener.start()
    
    def stop_listening(self):
        self.active = False
        if self.listener:
            self.listener.stop()
            self.listener = None
        self.current_keys.clear()
    
    def is_active(self) -> bool:
        return self.active