# Copyright (C) 2018 The NeoVintageous Team (NeoVintageous).
#
# This file is part of NeoVintageous.
#
# NeoVintageous is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# NeoVintageous is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with NeoVintageous.  If not, see <https://www.gnu.org/licenses/>.

import logging
import os
import time

from sublime import CLASS_WORD_START
from sublime import Region
from sublime_plugin import TextCommand
from sublime_plugin import WindowCommand

from NeoVintageous.nv import rc
from NeoVintageous.nv.ex.completions import iter_paths
from NeoVintageous.nv.ex.completions import parse_for_fs
from NeoVintageous.nv.ex.completions import parse_for_setting
from NeoVintageous.nv.ex_cmds import do_ex_cmd_edit_wrap
from NeoVintageous.nv.ex_cmds import do_ex_cmdline
from NeoVintageous.nv.ex_cmds import do_ex_command
from NeoVintageous.nv.ex_cmds import do_ex_user_cmdline
from NeoVintageous.nv.history import history_get
from NeoVintageous.nv.history import history_get_type
from NeoVintageous.nv.history import history_len
from NeoVintageous.nv.history import history_update
from NeoVintageous.nv.mappings import Mapping
from NeoVintageous.nv.mappings import mappings_is_incomplete
from NeoVintageous.nv.mappings import mappings_resolve
from NeoVintageous.nv.state import init_state
from NeoVintageous.nv.state import State
from NeoVintageous.nv.ui import ui_blink
from NeoVintageous.nv.ui import ui_cmdline_prompt
from NeoVintageous.nv.vi.cmd_base import ViMissingCommandDef
from NeoVintageous.nv.vi.cmd_defs import ViOpenNameSpace
from NeoVintageous.nv.vi.cmd_defs import ViOpenRegister
from NeoVintageous.nv.vi.cmd_defs import ViOperatorDef
from NeoVintageous.nv.vi.core import ViWindowCommandBase
from NeoVintageous.nv.vi.keys import key_names
from NeoVintageous.nv.vi.keys import KeySequenceTokenizer
from NeoVintageous.nv.vi.keys import to_bare_command_name
from NeoVintageous.nv.vi.settings import iter_settings
from NeoVintageous.nv.vi.utils import gluing_undo_groups
from NeoVintageous.nv.vi.utils import next_non_white_space_char
from NeoVintageous.nv.vi.utils import regions_transformer
from NeoVintageous.nv.vi.utils import translate_char
from NeoVintageous.nv.vim import INSERT
from NeoVintageous.nv.vim import INTERNAL_NORMAL
from NeoVintageous.nv.vim import message
from NeoVintageous.nv.vim import NORMAL
from NeoVintageous.nv.vim import OPERATOR_PENDING
from NeoVintageous.nv.vim import REPLACE
from NeoVintageous.nv.vim import SELECT
from NeoVintageous.nv.vim import VISUAL
from NeoVintageous.nv.vim import VISUAL_BLOCK
from NeoVintageous.nv.vim import VISUAL_LINE


__all__ = [
    '_nv_cmdline',
    '_nv_cmdline_feed_key',
    '_nv_ex_cmd_edit_wrap',
    '_nv_feed_key',
    '_nv_fix_st_eol_caret',
    '_nv_fs_completion',
    '_nv_goto_help',
    '_nv_process_notation',
    '_nv_replace_line',
    '_nv_run_cmds',
    '_nv_setting_completion',
    '_nv_write_fs_completion',
    'NeovintageousOpenMyRcFileCommand',
    'NeovintageousReloadMyRcFileCommand',
    'NeovintageousToggleSideBarCommand',
    'SequenceCommand'
]


_log = logging.getLogger(__name__)


class _nv_cmdline_feed_key(TextCommand):

    LAST_HISTORY_ITEM_INDEX = None

    def run(self, edit, key):
        if self.view.size() == 0:
            raise RuntimeError('expected a non-empty command-line')

        if self.view.size() == 1 and key not in ('<up>', '<C-n>', '<down>', '<C-p>', '<C-c>', '<C-[>'):
            return

        if key in ('<up>', '<C-p>'):
            # Recall older command-line from history, whose beginning matches
            # the current command-line.
            self._next_history(edit, backwards=True)

        elif key in ('<down>', '<C-n>'):
            # Recall more recent command-line from history, whose beginning
            # matches the current command-line.
            self._next_history(edit, backwards=False)

        elif key in ('<C-b>', '<home>'):
            # Cursor to beginning of command-line.
            self.view.sel().clear()
            self.view.sel().add(1)

        elif key in ('<C-c>', '<C-[>'):
            # Quit command-line without executing.
            self.view.window().run_command('hide_panel', {'cancel': True})

        elif key in ('<C-e>', '<end>'):
            # Cursor to end of command-line.
            self.view.sel().clear()
            self.view.sel().add(self.view.size())

        elif key == '<C-h>':
            # Delete the character in front of the cursor.
            pt_end = self.view.sel()[0].b
            pt_begin = pt_end - 1
            self.view.erase(edit, Region(pt_begin, pt_end))

        elif key == '<C-u>':
            # Remove all characters between the cursor position and the
            # beginning of the line.
            self.view.erase(edit, Region(1, self.view.sel()[0].end()))

        elif key == '<C-w>':
            # Delete the |word| before the cursor.
            word_region = self.view.word(self.view.sel()[0].begin())
            word_region = self.view.expand_by_class(self.view.sel()[0].begin(), CLASS_WORD_START)
            word_start_pt = word_region.begin()
            caret_end_pt = self.view.sel()[0].end()
            word_part_region = Region(max(word_start_pt, 1), caret_end_pt)
            self.view.erase(edit, word_part_region)
        else:
            raise NotImplementedError('unknown key')

    def _next_history(self, edit, backwards):
        if self.view.size() == 0:
            raise RuntimeError('expected a non-empty command-line')

        firstc = self.view.substr(0)
        if not history_get_type(firstc):
            raise RuntimeError('expected a valid command-line')

        if _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX is None:
            _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX = -1 if backwards else 0
        else:
            _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX += -1 if backwards else 1

        count = history_len(firstc)
        if count == 0:
            _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX = None

            return ui_blink()

        if abs(_nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX) > count:
            _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX = -count

            return ui_blink()

        if _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX >= 0:
            _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX = 0

            if self.view.size() > 1:
                return self.view.erase(edit, Region(1, self.view.size()))
            else:
                return ui_blink()

        if self.view.size() > 1:
            self.view.erase(edit, Region(1, self.view.size()))

        item = history_get(firstc, _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX)
        if item:
            self.view.insert(edit, 1, item)

    @staticmethod
    def reset_last_history_index():  # type: () -> None
        _nv_cmdline_feed_key.LAST_HISTORY_ITEM_INDEX = None


# TODO Replace with a functional api that commands can use directly.
class _nv_fix_st_eol_caret(TextCommand):

    # Tries to workaround some of the Sublime Text issues where the cursor caret
    # is positioned, off-by-one, at the end of line i.e. the caret positions
    # itself at >>>eol| |<<< instead of >>>eo|l|<<<. In some cases, the cursor
    # positions itself at >>>eol| |<<<, and then a second later,  moves to the
    # correct position >>>eo|l|<<< e.g. a left mouse click after the end of a
    # line. Some of these issues can't be worked-around e.g. the mouse click
    # issue described above.
    # See https://github.com/SublimeTextIssues/Core/issues/2121.

    def run(self, edit, mode=None):
        def f(view, s):
            if mode in (NORMAL, INTERNAL_NORMAL):
                pt = s.b
                if ((view.substr(pt) == '\n' or pt == view.size()) and not view.line(pt).empty()):
                    return Region(pt - 1)

            return s

        regions_transformer(self.view, f)


class _nv_goto_help(WindowCommand):

    def run(self):
        view = self.window.active_view()
        if not view:
            raise ValueError('view is required')

        if not view.sel():
            raise ValueError('selection is required')

        sel = view.sel()[0]

        score = view.score_selector(sel.b, 'text.neovintageous jumptag')
        # TODO ENHANCEMENT Allow goto to help for any word in a help file. See :h bar Anyway, you can use CTRL-] on any word, also when it is not within |, and Vim will try to find help for it.  Especially for options in single quotes, e.g. 'compatible'.  # noqa: E501
        if score == 0:
            return  # noop

        subject = view.substr(view.extract_scope(sel.b))
        if not subject:
            return  # noop

        if len(subject) > 35:
            return message('E149: Sorry, no help found')

        do_ex_command(self.window, 'help', {'subject': subject})


class _nv_run_cmds(TextCommand):

    def run(self, edit, commands):
        # Run a list of commands one after the other.
        #
        # Args:
        #   commands (list): A list of commands.
        for cmd, args in commands:
            self.view.run_command(cmd, args)


class _nv_feed_key(ViWindowCommandBase):

    def run(self, key, repeat_count=None, do_eval=True, check_user_mappings=True):
        start_time = time.time()

        _log.info('key evt: %s repeat_count=%s do_eval=%s check_user_mappings=%s', key, repeat_count, do_eval, check_user_mappings)  # noqa: E501

        try:
            self._feed_key(key, repeat_count, do_eval, check_user_mappings)
        except Exception as e:
            print('NeoVintageous: An error occurred during key press handle:')
            _log.exception(e)

            import sublime
            for window in sublime.windows():
                for view in window.views():
                    settings = view.settings()
                    settings.set('command_mode', False)
                    settings.set('inverse_caret_state', False)
                    settings.erase('vintage')

        _log.debug('key evt took %ss (key=%s repeat_count=%s do_eval=%s check_user_mappings=%s)', '{:.4f}'.format(time.time() - start_time), key, repeat_count, do_eval, check_user_mappings)  # noqa: E501

    def _feed_key(self, key, repeat_count=None, do_eval=True, check_user_mappings=True):
        # Args:
        #   key (str): Key pressed.
        #   repeat_count (int): Count to be used when repeating through the '.' command.
        #   do_eval (bool): Whether to evaluate the global state when it's in a
        #       runnable state. Most of the time, the default value of `True` should
        #       be used. Set to `False` when you want to manually control the global
        #       state's evaluation. For example, this is what the _nv_feed_key
        #       command does.
        #   check_user_mappings (bool):
        state = self.state

        mode = state.mode

        _log.debug('mode: %s', mode)

        # If the user has made selections with the mouse, we may be in an
        # inconsistent state. Try to remedy that.
        if (state.view.has_non_empty_selection_region() and mode not in (VISUAL, VISUAL_LINE, VISUAL_BLOCK, SELECT)):
            init_state(state.view)

        if key.lower() == '<esc>':
            self.window.run_command('_enter_normal_mode', {'mode': mode})
            state.reset_command_data()

            return

        state.sequence += key
        state.display_status()

        if state.must_capture_register_name:
            _log.debug('capturing register name...')
            state.register = key
            state.partial_sequence = ''

            return

        if state.must_collect_input:
            _log.debug('collecting input...')
            state.process_input(key)
            if state.runnable():
                _log.debug('state is runnable')
                if do_eval:
                    _log.debug('evaluating state...')
                    state.eval()
                    state.reset_command_data()

            return

        if repeat_count:
            state.action_count = str(repeat_count)

        if self._handle_count(state, key, repeat_count):
            _log.debug('handled count')

            return

        state.partial_sequence += key

        if check_user_mappings and mappings_is_incomplete(state.mode, state.partial_sequence):
            _log.debug('found incomplete mapping')

            return

        command = mappings_resolve(state, check_user_mappings=check_user_mappings)
        _log.debug('command %s %s', command, command.__class__.__mro__)

        if isinstance(command, ViOpenRegister):
            _log.debug('opening register...')
            state.must_capture_register_name = True

            return

        # XXX: This doesn't seem to be correct. If we are in OPERATOR_PENDING mode, we should
        # most probably not have to wipe the state.
        if isinstance(command, Mapping):
            _log.debug('found user mapping...')

            if do_eval:
                _log.debug('evaluating user mapping (mode=%s)...', state.mode)

                new_keys = command.mapping
                if state.mode == OPERATOR_PENDING:
                    new_keys = state.sequence[:-len(state.partial_sequence)] + command.mapping
                reg = state.register
                acount = state.action_count
                mcount = state.motion_count
                state.reset_command_data()
                state.register = reg
                state.motion_count = mcount
                state.action_count = acount

                _log.info('user mapping %s -> %s', command.sequence, new_keys)

                if ':' in new_keys:
                    do_ex_user_cmdline(self.window, new_keys)

                    return

                self.window.run_command('_nv_process_notation', {'keys': new_keys, 'check_user_mappings': False})

            return

        if isinstance(command, ViOpenNameSpace):
            # Keep collecting input to complete the sequence. For example, we
            # may have typed 'g'
            _log.info('opening namespace')

            return

        elif isinstance(command, ViMissingCommandDef):
            _log.info('found missing command...')

            bare_seq = to_bare_command_name(state.sequence)
            if state.mode == OPERATOR_PENDING:
                # We might be looking at a command like 'dd'. The first 'd' is
                # mapped for normal mode, but the second is missing in
                # operator pending mode, so we get a missing command. Try to
                # build the full command now.
                #
                # Exclude user mappings, since they've already been given a
                # chance to evaluate.
                command = mappings_resolve(state, sequence=bare_seq, mode=NORMAL, check_user_mappings=False)
            else:
                command = mappings_resolve(state, sequence=bare_seq)

            if isinstance(command, ViMissingCommandDef):
                _log.debug('unmapped sequence %s', state.sequence)
                state.mode = NORMAL
                state.reset_command_data()

                return ui_blink()

        if (state.mode == OPERATOR_PENDING and isinstance(command, ViOperatorDef)):
            _log.info('found operator pending...')
            # TODO: This may be unreachable code by now. ???
            # we're expecting a motion, but we could still get an action.
            # For example, dd, g~g~ or g~~
            # remove counts
            action_seq = to_bare_command_name(state.sequence)
            _log.debug('action sequence %s', action_seq)
            command = mappings_resolve(state, sequence=action_seq, mode=NORMAL)
            if isinstance(command, ViMissingCommandDef):
                _log.debug('unmapped sequence %s', state.sequence)
                state.reset_command_data()

                return

            if not command['motion_required']:
                state.mode = NORMAL

        state.set_command(command)

        if state.mode == OPERATOR_PENDING:
            state.reset_partial_sequence()

        if do_eval:
            _log.info('evaluating state...')
            state.eval()

    def _handle_count(self, state, key, repeat_count):
        """Return True if the processing of the current key needs to stop."""
        if not state.action and key.isdigit():
            if not repeat_count and (key != '0' or state.action_count):
                _log.debug('action count digit %s', key)
                state.action_count += key

                return True

        if (state.action and (state.mode == OPERATOR_PENDING) and key.isdigit()):
            if not repeat_count and (key != '0' or state.motion_count):
                _log.debug('motion count digit %s', key)
                state.motion_count += key

                return True


class _nv_process_notation(ViWindowCommandBase):

    def run(self, keys, repeat_count=None, check_user_mappings=True):
        # Args:
        #   keys (str): Key sequence to be run.
        #   repeat_count (int): Count to be applied when repeating through the
        #       '.' command.
        #   check_user_mappings (bool): Whether user mappings should be
        #       consulted to expand key sequences.
        state = self.state
        initial_mode = state.mode
        # Disable interactive prompts. For example, to supress interactive
        # input collection in /foo<CR>.
        state.non_interactive = True

        _log.debug('process notation keys %s for initial mode %s', keys, initial_mode)

        # First, run any motions coming before the first action. We don't keep
        # these in the undo stack, but they will still be repeated via '.'.
        # This ensures that undoing will leave the caret where the  first
        # editing action started. For example, 'lldl' would skip 'll' in the
        # undo history, but store the full sequence for '.' to use.
        leading_motions = ''
        for key in KeySequenceTokenizer(keys).iter_tokenize():
            self.window.run_command('_nv_feed_key', {
                'key': key,
                'do_eval': False,
                'repeat_count': repeat_count,
                'check_user_mappings': check_user_mappings
            })
            if state.action:
                # The last key press has caused an action to be primed. That
                # means there are no more leading motions. Break out of here.
                _log.debug('first action found in %s', state.sequence)
                state.reset_command_data()
                if state.mode == OPERATOR_PENDING:
                    state.mode = NORMAL

                break

            elif state.runnable():
                # Run any primed motion.
                leading_motions += state.sequence
                state.eval()
                state.reset_command_data()

            else:
                # XXX: When do we reach here?
                state.eval()

        if state.must_collect_input:
            # State is requesting more input, so this is the last command in
            # the sequence and it needs more input.
            self.collect_input()
            return

        # Strip the already run commands
        if leading_motions:
            if ((len(leading_motions) == len(keys)) and (not state.must_collect_input)):
                state.non_interactive = False
                return

            _log.debug('original keys/leading-motions: %s/%s', keys, leading_motions)
            keys = keys[len(leading_motions):]
            _log.debug('keys stripped to %s', keys)

        if not (state.motion and not state.action):
            with gluing_undo_groups(self.window.active_view(), state):
                try:
                    for key in KeySequenceTokenizer(keys).iter_tokenize():
                        if key.lower() == key_names.ESC:
                            # XXX: We should pass a mode here?
                            self.window.run_command('_enter_normal_mode')
                            continue

                        elif state.mode not in (INSERT, REPLACE):
                            self.window.run_command('_nv_feed_key', {
                                'key': key,
                                'repeat_count': repeat_count,
                                'check_user_mappings': check_user_mappings
                            })
                        else:
                            self.window.run_command('insert', {
                                'characters': translate_char(key)
                            })

                    if not state.must_collect_input:
                        return

                finally:
                    state.non_interactive = False
                    # Ensure we set the full command for "." to use, but don't
                    # store "." alone.
                    if (leading_motions + keys) not in ('.', 'u', '<C-r>'):
                        state.repeat_data = ('vi', (leading_motions + keys), initial_mode, None)

        # We'll reach this point if we have a command that requests input whose
        # input parser isn't satistied. For example, `/foo`. Note that
        # `/foo<CR>`, on the contrary, would have satisfied the parser.

        _log.debug('unsatisfied parser action = %s, motion=%s', state.action, state.motion)

        if (state.action and state.motion):
            # We have a parser an a motion that can collect data. Collect data
            # interactively.
            motion_data = state.motion.translate(state) or None

            if motion_data is None:
                state.reset_command_data()

                return ui_blink()

            motion_data['motion_args']['default'] = state.motion._inp

            self.window.run_command(motion_data['motion'], motion_data['motion_args'])

            return

        self.collect_input()

    def collect_input(self):
        try:
            command = None
            if self.state.motion and self.state.action:
                if self.state.motion.accept_input:
                    command = self.state.motion
                else:
                    command = self.state.action
            else:
                command = self.state.action or self.state.motion

            parser_def = command.input_parser
            if parser_def.interactive_command:

                self.window.run_command(
                    parser_def.interactive_command,
                    {parser_def.input_param: command._inp}
                )
        except IndexError:
            _log.debug('could not find a command to collect more user input')
            ui_blink()
        finally:
            self.state.non_interactive = False


class _nv_replace_line(TextCommand):

    def run(self, edit, with_what):
        b = self.view.line(self.view.sel()[0].b).a
        pt = next_non_white_space_char(self.view, b, white_space=' \t')
        self.view.replace(edit, Region(pt, self.view.line(pt).b), with_what)


class _nv_ex_cmd_edit_wrap(TextCommand):

    # This command is required to wrap ex commands that need a Sublime Text edit
    # token. Edit tokens can only be obtained from a TextCommand. Some ex
    # commands don't need an edit token, those commands don't need to be wrapped
    # by a text command.

    def run(self, edit, **kwargs):
        do_ex_cmd_edit_wrap(self, edit, **kwargs)


class _nv_cmdline(WindowCommand):

    interactive_call = True

    def is_enabled(self):
        # TODO refactor into a text command as the view is always required?
        return bool(self.window.active_view())

    def run(self, cmdline=None, initial_text=None):
        _log.debug('cmdline.run cmdline = %s', cmdline)

        if cmdline:

            # The caller has provided a command (non-interactive mode), so run
            # the command without a prompt.
            # TODO [review] Non-interactive mode looks unused?

            _nv_cmdline.interactive_call = False

            return self.on_done(cmdline)
        else:
            _nv_cmdline.interactive_call = True

        # TODO There has got to be a better way to handle fs ("file system"?) completions.
        _nv_fs_completion.invalidate()

        state = State(self.window.active_view())
        state.reset_during_init = False

        if initial_text is None:
            if state.mode in (VISUAL, VISUAL_LINE, VISUAL_BLOCK):
                initial_text = ":'<,'>"
            else:
                initial_text = ':'
        else:
            if initial_text[0] != ':':
                raise ValueError('initial cmdline text must begin with a colon')

        ui_cmdline_prompt(
            self.window,
            initial_text=initial_text,
            on_done=self.on_done,
            on_change=self.on_change,
            on_cancel=self.on_cancel
        )

    def on_change(self, s):
        if s == '':
            return self._force_cancel()

        if len(s) <= 1:
            return

        if s[0] != ':':
            return self._force_cancel()

        if _nv_cmdline.interactive_call:
            cmd, prefix, only_dirs = parse_for_fs(s)
            if cmd:
                _nv_fs_completion.prefix = prefix
                _nv_fs_completion.is_stale = True
            cmd, prefix, _ = parse_for_setting(s)
            if cmd:
                _nv_setting_completion.prefix = prefix
                _nv_setting_completion.is_stale = True

            if not cmd:
                return

        _nv_cmdline.interactive_call = True

    def on_done(self, cmdline):
        if len(cmdline) <= 1:
            return

        if cmdline[0] != ':':
            return

        if _nv_cmdline.interactive_call:
            history_update(cmdline)

        _nv_cmdline_feed_key.reset_last_history_index()

        do_ex_cmdline(self.window, cmdline)

    def _force_cancel(self):
        self.on_cancel()
        self.window.run_command('hide_panel', {'cancel': True})

    def on_cancel(self):
        _nv_cmdline_feed_key.reset_last_history_index()


class _nv_write_fs_completion(TextCommand):
    def run(self, edit, cmd, completion):
        if self.view.score_selector(0, 'text.excmdline') == 0:
            return

        _nv_cmdline.interactive_call = False

        self.view.sel().clear()
        self.view.replace(edit, Region(0, self.view.size()), cmd + ' ' + completion)
        self.view.sel().add(Region(self.view.size()))


class _nv_fs_completion(TextCommand):
    # Last user-provided path string.
    prefix = ''
    frozen_dir = ''
    is_stale = False
    items = None

    @staticmethod
    def invalidate():  # type: () -> None
        _nv_fs_completion.prefix = ''
        _nv_fs_completion.frozen_dir = ''
        _nv_fs_completion.is_stale = True
        _nv_fs_completion.items = None

    def run(self, edit):
        if self.view.score_selector(0, 'text.excmdline') == 0:
            return

        state = State(self.view)
        _nv_fs_completion.frozen_dir = (_nv_fs_completion.frozen_dir or
                                        (state.settings.vi['_cmdline_cd'] + '/'))

        cmd, prefix, only_dirs = parse_for_fs(self.view.substr(self.view.line(0)))
        if not cmd:
            return

        if not (_nv_fs_completion.prefix or _nv_fs_completion.items) and prefix:
            _nv_fs_completion.prefix = prefix
            _nv_fs_completion.is_stale = True

        if prefix == '..':
            _nv_fs_completion.prefix = '../'
            self.view.run_command('_nv_write_fs_completion', {
                'cmd': cmd,
                'completion': '../'
            })

        if prefix == '~':
            path = os.path.expanduser(prefix) + '/'
            _nv_fs_completion.prefix = path
            self.view.run_command('_nv_write_fs_completion', {
                'cmd': cmd,
                'completion': path
            })

            return

        if (not _nv_fs_completion.items) or _nv_fs_completion.is_stale:
            _nv_fs_completion.items = iter_paths(from_dir=_nv_fs_completion.frozen_dir,
                                                 prefix=_nv_fs_completion.prefix,
                                                 only_dirs=only_dirs)
            _nv_fs_completion.is_stale = False

        try:
            self.view.run_command('_nv_write_fs_completion', {
                'cmd': cmd,
                'completion': next(_nv_fs_completion.items)
            })
        except StopIteration:
            _nv_fs_completion.items = iter_paths(prefix=_nv_fs_completion.prefix,
                                                 from_dir=_nv_fs_completion.frozen_dir,
                                                 only_dirs=only_dirs)

            self.view.run_command('_nv_write_fs_completion', {
                'cmd': cmd,
                'completion': _nv_fs_completion.prefix
            })


class _nv_setting_completion(TextCommand):
    # Last user-provided path string.
    prefix = ''
    is_stale = False
    items = None

    @staticmethod
    def invalidate():  # type: () -> None
        _nv_setting_completion.prefix = ''
        _nv_setting_completion.is_stale = True
        _nv_setting_completion.items = None

    def run(self, edit):
        if self.view.score_selector(0, 'text.excmdline') == 0:
            return

        cmd, prefix, _ = parse_for_setting(self.view.substr(self.view.line(0)))
        if not cmd:
            return

        if (_nv_setting_completion.prefix is None) and prefix:
            _nv_setting_completion.prefix = prefix
            _nv_setting_completion.is_stale = True
        elif _nv_setting_completion.prefix is None:
            _nv_setting_completion.items = iter_settings('')
            _nv_setting_completion.is_stale = False

        if not _nv_setting_completion.items or _nv_setting_completion.is_stale:
            _nv_setting_completion.items = iter_settings(_nv_setting_completion.prefix)
            _nv_setting_completion.is_stale = False

        try:
            self.view.run_command('_nv_write_fs_completion', {
                'cmd': cmd,
                'completion': next(_nv_setting_completion.items)
            })
        except StopIteration:
            try:
                _nv_setting_completion.items = iter_settings(_nv_setting_completion.prefix)
                self.view.run_command('_nv_write_fs_completion', {
                    'cmd': cmd,
                    'completion': next(_nv_setting_completion.items)
                })
            except StopIteration:
                return


class NeovintageousOpenMyRcFileCommand(WindowCommand):

    def run(self):
        rc.open(self.window)


class NeovintageousReloadMyRcFileCommand(WindowCommand):

    def run(self):
        rc.reload()


class NeovintageousToggleSideBarCommand(WindowCommand):

    def run(self):
        self.window.run_command('toggle_side_bar')

        if self.window.is_sidebar_visible():
            self.window.run_command('focus_side_bar')
        else:
            self.window.focus_group(self.window.active_group())


# DEPRECATED Use _nv_run_cmds instead
class SequenceCommand(TextCommand):

    def run(self, edit, commands):
        # Run a list of commands one after the other.
        #
        # Args:
        #   commands (list): A list of commands.
        for cmd, args in commands:
            self.view.run_command(cmd, args)
