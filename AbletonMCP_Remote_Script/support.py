from __future__ import absolute_import, print_function, unicode_literals

# Change queue import for Python 2.
try:
    import Queue as queue
except ImportError:
    import queue

try:
    _INTEGER_TYPES = (int, long)
except NameError:
    _INTEGER_TYPES = (int,)

try:
    _STRING_TYPES = (basestring,)
except NameError:
    _STRING_TYPES = (str,)

try:
    from .plugin_params import (
        attach_groups,
        classify_device,
        filter_parameters,
        find_parameter,
        is_plugin_class,
        mapping_coverage,
        normalize_param_key,
        plugin_configure_note,
        try_find_parameter,
    )
except (ImportError, ValueError):
    from plugin_params import (
        attach_groups,
        classify_device,
        filter_parameters,
        find_parameter,
        is_plugin_class,
        mapping_coverage,
        normalize_param_key,
        plugin_configure_note,
        try_find_parameter,
    )

# Constants for socket communication.
DEFAULT_PORT = 9877
HOST = "localhost"

_ARRANGEMENT_ENVELOPE_NOTE = (
    "Arrangement clip automation is not in the public LOM (it lives on the track). "
    "Arrangement clips only have modulation, which this API does not expose. "
    "Use session clips for clip envelopes."
)
_MOVE_DEVICE_INSTRUMENT_MSG = (
    "Live cannot place an instrument before MIDI effects. "
    "load_instrument_or_effect already inserts MIDI FX before the instrument; "
    "use move_device only to reorder MIDI effects (or audio effects)."
)
