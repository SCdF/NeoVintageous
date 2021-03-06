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

from sublime import active_window
from sublime import DRAW_EMPTY_AS_OVERWRITE
from sublime import DRAW_NO_FILL
from sublime import DRAW_NO_OUTLINE
from sublime import DRAW_SOLID_UNDERLINE
from sublime import DRAW_SQUIGGLY_UNDERLINE
from sublime import DRAW_STIPPLED_UNDERLINE
from sublime import set_timeout

from NeoVintageous.nv.vim import status_message


# TODO Implement bell. See :h 'belloff'. 'belloff' defaults to 'all' in Neovim. See https://github.com/neovim/neovim/issues/2676.  # noqa: E501
# TODO How to make the bell theme adaptive i.e. work nice in light AND dark color schemes.
def _ui_bell():
    window = active_window()

    view = window.active_view()
    if not view:
        return

    settings = view.settings()

    if settings.get('vintageous_belloff') == 'all':
        return

    theme = 'Packages/NeoVintageous/res/Bell.tmTheme'

    duration = int(0.3 * 1000)

    if settings.get('vintageous_wip_bell_all_active_views'):
        views = []
        for group in range(window.num_groups()):
            view = window.active_view_in_group(group)
            if view:
                settings = settings
                settings.set('color_scheme', theme)
                views.append(view)

        def remove_bell():
            for view in views:
                settings.erase('color_scheme')

        set_timeout(remove_bell, duration)

    else:
        def remove_bell():
            settings.erase('color_scheme')

        settings.set('color_scheme', theme)
        set_timeout(remove_bell, duration)


# TODO [refactor] Rework this to use the _ui_bell().
# TODO [refactor] Rework this to require a view or settings object.
def ui_blink(msg=None, times=4, delay=55):
    if msg:
        status_message(msg)

    view = active_window().active_view()
    if not view:
        return

    settings = view.settings()

    if settings.get('vintageous_belloff') == 'all':
        return

    if settings.get('vintageous_wip'):
        return _ui_bell()

    # Ensure we leave the setting as we found it.
    times = times if (times % 2) == 0 else times + 1

    def do_blink():
        nonlocal times
        if times > 0:
            settings.set('highlight_line', not settings.get('highlight_line'))
            times -= 1
            set_timeout(do_blink, delay)

    do_blink()


def ui_cmdline_prompt(window, initial_text, on_done, on_change, on_cancel):
    # type: (...) -> None
    input_panel = window.show_input_panel(
        '',
        initial_text,
        on_done,
        on_change,
        on_cancel
    )

    input_panel.set_name('Command-line mode')

    _set = input_panel.settings().set

    # Mark the input panel as a widget.
    #
    # XXX This doesn't always work as expected, because the input panel is
    # already created before we setapply the settings, so there is a race-
    # condition.
    #
    # TODO [review] See if creating a Command-line mode.sublime-settings file
    # with all the relevant settings, including the "is_widget" setting solves
    # the race-condition issue described above.
    _set('is_widget', True)
    _set('is_vintageous_widget', True)

    _set('auto_complete', False)
    _set('auto_indent', False)
    _set('auto_match_enabled', False)
    _set('draw_centered', False)
    _set('draw_indent_guides', False)
    _set('gutter', False)
    _set('margin', 1)
    _set('match_selection', False)
    _set('rulers', [])
    _set('scroll_past_end', False)
    _set('smart_indent', False)
    _set('translate_tabs_to_spaces', False)
    _set('word_wrap', False)

    input_panel.assign_syntax(
        'Packages/NeoVintageous/res/Command-line mode.sublime-syntax')


_REGION_FLAGS = {
    'fill': DRAW_NO_OUTLINE,
    'outline': DRAW_NO_FILL,
    'squiggly_underline': DRAW_SQUIGGLY_UNDERLINE | DRAW_NO_FILL | DRAW_NO_OUTLINE | DRAW_EMPTY_AS_OVERWRITE,
    'stippled_underline': DRAW_STIPPLED_UNDERLINE | DRAW_NO_FILL | DRAW_NO_OUTLINE | DRAW_EMPTY_AS_OVERWRITE,
    'underline': DRAW_SOLID_UNDERLINE | DRAW_NO_FILL | DRAW_NO_OUTLINE | DRAW_EMPTY_AS_OVERWRITE,
}


def ui_region_flags(name):
    return _REGION_FLAGS.get(name)
