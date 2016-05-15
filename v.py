import neovim
import keys

import os
import sys
import os_code
import time
import threading
from trollius import py33_exceptions

class V:
    def __init__(self, args):
        self.args = args

        if args["-d"]:
            nvim_launcher_thread = threading.Thread(target=self.__call_nvim__) #Launch nvim in new thread so that V doesn't hang
            nvim_launcher_thread.start()
            time.sleep(1)
            socket = os_code.get_socket_path(args["platform"])

            try:
                self.nvim_instance = neovim.attach("socket", path=socket)
            except py33_exceptions.FileNotFoundError:
                sys.stderr.write("Couldn't connect to nvim. Did you export your NVIM_LIST_ADDRESS?\n\n")
                sys.exit()

        else:
            args = os_code.get_embedded_nvim_args(args["platform"], args["-f"], args["-w"])
            try:
                self.nvim_instance = neovim.attach("child", argv=args)
            except py33_exceptions.FileNotFoundError:
                sys.stderr.write("Couldn't find the neovim executable! Is nvim in your $PATH?\n\n")
                sys.exit()
            
        self.active_reg = "a"
        self.pending_number = ""
        self.recorded_text = ""
        self.loop_symbol = ""
        self.recording = False
        self.pending_command = ""
        self.keys_sent = []

    def __call_nvim__(self):
        socket = os_code.get_socket_path(self.args["platform"])

        arg = os_code.get_external_nvim_command(self.args["platform"], self.args["-f"], self.args['-w'])
        os.system(arg)

    
    def key_stroke(self, key):
        self.keys_sent.append(key)
        if self.recording:
            if key == self.loop_symbol:
                self.recording = False
                function_index = keys.loop_keys.index(key)
                keys.loop_functions[function_index](self)
                
            else:
                self.recorded_text += key
        elif self.pending_command != "" or key in keys.normal_keys:
            self.pending_command += key
            function_index = keys.normal_keys.index(self.pending_command[:1])
            keys.normal_functions[function_index](self)
        elif key in keys.loop_keys:
            self.recording = True
            self.loop_symbol = key
        elif key.isdigit():
            self.pending_number += key
        else:
            self.nvim_instance.input(self.pending_number + key)
            self.pending_number = ""

    def set_register(self, register, value):
        command = ":let @{}='{}'".format(register, value)
        try:
            self.nvim_instance.command(command)
            return True
        except:
            return False

    def get_mode(self):
        return self.nvim_instance.eval("mode(1)")

    def get_register(self, register):
        command = ":echo @{}".format(register)
        try:
            return self.nvim_instance.command_output(command)[1:]
        except:
            return False

    def get_text(self):
        for line in self.nvim_instance.buffers:
            yield line

    def close(self):
        if not self.args["-d"]:
            exit_commands = ":q!" + keys.enter
            self.nvim_instance.input(exit_commands)


    def clean_up(self):
        if self.get_mode() == "i":
            self.key_stroke(keys.esc)

        if self.recording:
            self.key_stroke(self.loop_symbol)
