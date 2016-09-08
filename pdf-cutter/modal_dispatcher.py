### modal_dispatcher.py
### The thing that handles keyboard modes dispatch for us

from __future__ import with_statement

from PyQt4 import QtCore
from string import capwords

class DontWannaStart(Exception):
    pass

KEYNAMES_EXCEPTION_TABLE = {
    "sys_req" : QtCore.Qt.Key_SysReq,
    "page_up" : QtCore.Qt.Key_PageUp,
    "page_down" : QtCore.Qt.Key_PageDown,
    "alt_gr" : QtCore.Qt.Key_AltGr,
    "caps_lock" : QtCore.Qt.Key_CapsLock,
    "num_lock" : QtCore.Qt.Key_NumLock,
    "scroll_lock" : QtCore.Qt.Key_ScrollLock,
    "quote_dbl" : QtCore.Qt.Key_QuoteDbl,
    "number_sign" : QtCore.Qt.Key_NumberSign,
    "paren_left" : QtCore.Qt.Key_ParenLeft,
    "paren_right" : QtCore.Qt.Key_ParenRight,
    "bracket_left" : QtCore.Qt.Key_BracketLeft,
    "bracket_right" : QtCore.Qt.Key_BracketRight,
    "ascii_circum" : QtCore.Qt.Key_AsciiCircum,
    "quote_left" : QtCore.Qt.Key_QuoteLeft,
    "brace_left" : QtCore.Qt.Key_BraceLeft,
    "brace_right" : QtCore.Qt.Key_BraceRight,
    "ascii_tilde" : QtCore.Qt.Key_AsciiTilde,
    # "no_break_space" : QtCore.Qt.nobreakspace,
    # "exclamdown" : QtCore.Qt.exclamdown,
    # "cent" : QtCore.Qt.cent,
    # "sterling" : QtCore.Qt.sterling,
    # "currency" : QtCore.Qt.currency,
    # "yen" : QtCore.Qt.yen,
    # "broken_bar" : QtCore.Qt.brokenbar,
    # "section" : QtCore.Qt.section,
    # "diaeresis" : QtCore.Qt.diaeresis,
    # "copyright" : QtCore.Qt.copyright
    # there are more of these, but I'm lazy right now
    }

def qt_key_from_string(key):
    if KEYNAMES_EXCEPTION_TABLE.has_key(key):
        return KEYNAMES_EXCEPTION_TABLE[key]

    return getattr(QtCore.Qt, "Key_" + capwords(key, "_"))

class ModalDispatcher(object):
    def __init__(self, keymap_description):
        self.parse_keymap_description(keymap_description)

    def parse_keymap_description(self, keymap_description):
        # first we list all the available actions
        actions = keymap_description["actions"]
        self.action_starters = {}
        self.action_stoppers = {}
        for action in actions:
            self.action_starters[action[0]] = action[1]
            self.action_stoppers[action[0]] = action[2]

        self.mode_descriptions = keymap_description.copy()
        self.mode_descriptions.pop("actions", None)

        self.mode_stack = []
        self.current_mode = Mode(None, self.mode_descriptions['main'])
        self.action = None
        
    def action_starter(self, name):
        return self.action_starters[name]

    def action_stopper(self, name):
        return self.action_stoppers[name]
    
    def press(self, key):
        if self.mode_key_p(key):
            self.try_activate_mode(key)
        elif self.action_key_p(key):
            self.try_start_action(key)

    def mode_key_p(self, key):
        return self.current_mode.modes.has_key(key)

    def action_key_p(self, key):
        return self.current_mode.actions.has_key(key)

    def try_activate_mode(self, key):
        print "Trying to activate mode", key
        if self.action is not None:
            return

        with locking_attr(self):
            mode_name = self.current_mode.modes[key]
            print "Mode name is", mode_name
            self.mode_stack.append([mode_name, key, self.current_mode])
            self.current_mode = Mode(self.current_mode,
                                     self.mode_descriptions[mode_name])
            if hasattr(self.current_mode, "on_start"):
                self.current_mode.on_start()
            print "Mode activated:", mode_name

    def try_start_action(self, key):
        print "Trying to start action", key
        if self.action is not None:
            return

        self.action = 'lock'
        action_name_and_args = self.current_mode.actions[key]
        try:
            apply(self.action_starter(action_name_and_args[0]),
                  action_name_and_args[1:])
        except DontWannaStart:
            print "Got dont wanna start"
            self.action = None
        except Exception:
            self.action = None
            raise
        else:
            self.action = action_name_and_args

    def release(self, key):
        if self.mode_in_stack_key_p(key):
            self.unwind_mode_stack(key)
        elif self.action_key_p(key):
            self.try_stop_action(key)

    def mode_in_stack_key_p(self, key):
        lst = filter(lambda x: x[1] == key,
                     self.mode_stack)
        return len(lst) == 1
            
    def unwind_mode_stack(self, key):
        self.stop_current_action()

        print "UNWIND MODE STACK", self.mode_stack
        with locking_attr(self):
            if hasattr(self.current_mode, "on_stop"):
                self.current_mode.on_stop()
            
            while self.mode_stack[-1][1] != key:
                (_, _, it) = self.mode_stack.pop()
                if hasattr(it, "on_stop"):
                    it.on_stop()
            (_, _, old_mode) = self.mode_stack.pop()
            self.current_mode = old_mode

    def stop_current_action(self):
        if self.action is None:
            return

        action = self.action
        self.action = 'lock'
        apply(self.action_stopper(action[0]), action[1:])
        self.action = None

    def try_stop_action(self, key):
        if self.action is None:
            return

        if self.action == self.current_mode.actions[key]:
            self.stop_current_action()
            
def locking_attr(x, attr_name="action", value_after=None):
    class Frob(object):
        def __enter__(self):
            it = getattr(x, attr_name)
            if it is not None:
                raise Exception("Attempt to lock a not-None field " + str(it))

            setattr(x, attr_name, 'lock')
            return True
            
        def __exit__(self, type, value, traceback):
            setattr(x, attr_name, value_after)
            return False

    return Frob()
    
class Mode(object):
    def __init__(self, old_mode, description):
        self.modes = {}
        self.actions = {}

        self.copy_if_inherit(old_mode, description)

        options = description.get('options', {})
        it = options.get('on_start', None)
        if it:
            self.on_start = it
        it = options.get('on_stop', None)
        if it:
            self.on_stop = it

        for (key, spec) in description.iteritems():
            if key == 'options':
                continue
            
            if isinstance(spec, basestring):
                spec = [spec]

            if spec[0] == 'mode':
                self.modes[qt_key_from_string(key)] = spec[1]
            else:
                self.actions[qt_key_from_string(key)] = spec
        print "Modes", self.modes, "actions", self.actions

    def copy_if_inherit(self, old_mode, description):
        if 'inherit' in description.get('options', {}):
            self.modes = old_mode.modes.copy()
            self.actions = old_mode.actions.copy()
