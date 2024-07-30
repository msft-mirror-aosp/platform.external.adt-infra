# Define a fake internal modeule name to allow tkinter to be found when
# mouseinfo is called as mouseinfo. This only works if mouseinfo is not use by
# any other tests. This is needed as tkinter is part of the standard library and
# tkinter is always imported when pyautogui is requested.

import sys
import types

try:
    import tkinter
except ImportError:
    # Tkinter may not be available on some Python distributions
    sys.modules['tkinter'] = types.ModuleType('tkinter')
    # Make the pymsgbox methods dependent on tkinter unavailable
    def _couldNotImportPyMsgBox(*unused_args, **unused_kwargs):
        raise ImportError(
            "PyAutoGUI was unable to import pymsgbox. " + \
            "Please install tkinter in order to use this function."
        )
    pymsgbox = types.ModuleType('pymsgbox')
    pymsgbox.alert = pymsgbox.confirm = pymsgbox.prompt = pymsgbox.password = _couldNotImportPyMsgBox
    sys.modules['pymsgbox'] = pymsgbox

    # Mouseinfo also depends on tkinter
    def _MouseInfoWindow():
        raise ImportError(
            "Mouseinfo was unable to import tkinter. " + \
            "Please install tkinter in order to use this function."
        )
    mouseinfo = types.ModuleType('mouseinfo')
    mouseinfo.MouseInfoWindow = _MouseInfoWindow
    sys.modules['mouseinfo'] = mouseinfo
