"""Pure helpers for plugin/device parameter lookup. No Live imports.

Copied into Live's AbletonMCP folder next to __init__.py on deploy.
"""

from __future__ import absolute_import, print_function, unicode_literals

PLUGIN_CLASS_NAMES = ("PluginDevice", "AuPluginDevice")

_LOM_TYPE = {
    0: "undefined",
    1: "instrument",
    2: "audio_effect",
    4: "midi_effect",
}

_CONFIGURE_NOTE = (
    "Live only exposes plug-in parameters that are in the device Configure panel "
    "(hard cap about 128). There is no LOM command to add every host-automatable "
    "knob in one click. After Configure, right-click the device title bar and "
    "choose Save as Default Configuration, or save an .adg Instrument Rack, so "
    "new instances keep the list. Optional Live Options.txt: "
    "-_PluginAutoPopulateThreshold=128 auto-fills the first 128 on new instances only."
)


def lom_type_name(type_code):
    try:
        code = int(type_code)
    except (TypeError, ValueError):
        return "unknown"
    return _LOM_TYPE.get(code, "unknown")


def classify_device(class_name, class_display_name, type_code, can_have_drum_pads, can_have_chains):
    if can_have_drum_pads:
        return "drum_machine"
    if can_have_chains:
        return "rack"
    lom = lom_type_name(type_code)
    class_name = class_name or ""
    class_display_name = class_display_name or ""
    if class_name in PLUGIN_CLASS_NAMES:
        if lom in ("instrument", "audio_effect", "midi_effect"):
            return lom
        return "plugin"
    blob = " ".join([class_name, class_display_name, lom]).lower()
    if "midi_effect" in blob or lom == "midi_effect":
        return "midi_effect"
    if lom == "instrument" or "instrument" in blob:
        return "instrument"
    if lom == "audio_effect" or "audio_effect" in blob:
        return "audio_effect"
    return "unknown"


def is_plugin_class(class_name):
    return (class_name or "") in PLUGIN_CLASS_NAMES


def normalize_param_key(name):
    if name is None:
        return ""
    return "".join(ch.lower() for ch in str(name) if ch.isalnum())


def parameter_group(name, device_name=""):
    """Semantic group for a Configure-panel name. Live itself has no plugin param folders."""
    raw = str(name or "").strip()
    if not raw:
        return "Other"
    lower = raw.lower()
    if ">" in raw:
        return "Filter routing"
    if lower == "device on" or lower.startswith("device on"):
        return "Device"
    if lower.startswith("macro"):
        return "Macros"
    if lower.startswith("noise"):
        return "Noise"
    if lower.startswith("sub"):
        return "Sub oscillator"
    if lower.startswith("main") or lower in ("master vol", "master volume", "mastervol"):
        return "Main"
    if lower.startswith("clip player") or lower.startswith("arp"):
        return "Playback"
    if lower in ("key", "scale") or lower.startswith("scale "):
        return "Scale"
    if lower == "swing" or lower.startswith("swing "):
        return "Groove"
    if lower in (
        "pitch bend", "bend up", "bend down", "mod wheel", "transpose",
        "porta time", "porta curve", "porta always", "mono toggle", "legato",
    ) or lower.startswith("porta") or lower.startswith("bend "):
        return "Voice"
    parts = raw.split()
    if len(parts) >= 2:
        head = parts[0].lower()
        second = parts[1]
        if head == "filter" and second.isdigit():
            return "Filter {0}".format(second)
        if head in ("env", "envelope") and second.isdigit():
            return "Envelope {0}".format(second)
        if head == "lfo" and second.isdigit():
            return "LFO {0}".format(second)
    if parts and parts[0] in ("A", "B", "C"):
        return "Oscillator {0}".format(parts[0])
    return "Other"


def attach_groups(params, device_name=""):
    grouped = []
    order = []
    buckets = {}
    for param in params:
        group = param.get("group") or parameter_group(param.get("name"), device_name)
        item = dict(param)
        item["group"] = group
        grouped.append(item)
        if group not in buckets:
            order.append(group)
            buckets[group] = []
        buckets[group].append({"index": item.get("index"), "name": item.get("name")})
    groups = []
    for name in order:
        groups.append({
            "name": name,
            "count": len(buckets[name]),
            "parameters": buckets[name],
        })
    return grouped, groups


def param_query_matches(param, query):
    if query is None:
        return True
    text = str(query).strip()
    if not text:
        return True
    lowered = text.lower()
    key = normalize_param_key(text)
    fields = [
        param.get("name"),
        param.get("original_name"),
        param.get("display_value"),
        param.get("group"),
    ]
    for field in fields:
        if not field:
            continue
        raw = str(field)
        if lowered in raw.lower():
            return True
        if key and key in normalize_param_key(raw):
            return True
    return False


def filter_parameters(params, query):
    if query is None or str(query).strip() == "":
        return list(params)
    text = str(query).strip()
    exact_group = [p for p in params if str(p.get("group") or "").lower() == text.lower()]
    if exact_group:
        return exact_group
    return [p for p in params if param_query_matches(p, query)]


def find_parameter(params, index=None, name=None):
    if index is not None:
        for param in params:
            if param.get("index") == index:
                return param
        raise IndexError("Parameter index out of range")
    if name is None or str(name).strip() == "":
        raise ValueError("parameter_index or parameter_name is required")
    needle = str(name).strip()
    needle_key = normalize_param_key(needle)
    exact = []
    partial = []
    seen_exact = set()
    seen_partial = set()
    for param in params:
        names = [param.get("name"), param.get("original_name")]
        matched_exact = False
        for raw in names:
            if raw is None or raw == "":
                continue
            text = str(raw)
            if text.lower() == needle.lower() or (
                needle_key and normalize_param_key(text) == needle_key
            ):
                idx = param.get("index")
                if idx not in seen_exact:
                    exact.append(param)
                    seen_exact.add(idx)
                matched_exact = True
                break
        if matched_exact:
            continue
        for raw in names:
            if raw is None or raw == "":
                continue
            if needle_key and needle_key in normalize_param_key(raw):
                idx = param.get("index")
                if idx not in seen_partial:
                    partial.append(param)
                    seen_partial.add(idx)
                break
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        names = ", ".join(p.get("name") or "?" for p in exact)
        raise ValueError("parameter name is ambiguous: {0}".format(names))
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        names = ", ".join(p.get("name") or "?" for p in partial)
        raise ValueError("parameter name is ambiguous: {0}".format(names))
    raise ValueError(
        "parameter name not found: {0} (not in this instance's Configure panel; "
        "do not reuse parameter indices across mappings)".format(needle)
    )


def try_find_parameter(params, index=None, name=None):
    try:
        return find_parameter(params, index=index, name=name)
    except (IndexError, ValueError):
        return None


# Sound-design names agents commonly want. Presence is per Configure mapping.
SERUM_CORE_NAMES = (
    "Main Vol",
    "A Enable", "A Level", "A WT Pos", "A Unison", "A Uni Detune", "A Warp",
    "B Enable", "B Level", "B WT Pos", "B Density", "B Grain Length",
    "C Enable", "C Level", "C WT Pos",
    "Filter 1 On", "Filter 1 Type", "Filter 1 Freq", "Filter 1 Res", "Filter 1 Drive",
    "Filter 2 On", "Filter 2 Freq", "Filter 2 Res",
    "Env 1 Attack", "Env 1 Decay", "Env 1 Sustain", "Env 1 Release",
    "Macro 1", "Macro 2", "Macro 3", "Macro 4",
    "LFO 1 Rate", "LFO 2 Rate",
    "Noise Level", "Sub Level",
)


def is_serum_device(device_name):
    blob = str(device_name or "").lower()
    return "serum" in blob


def mapping_coverage(params, device_name=""):
    if not is_serum_device(device_name):
        return None
    present_keys = set()
    for param in params:
        present_keys.add(normalize_param_key(param.get("name")))
        orig = param.get("original_name")
        if orig:
            present_keys.add(normalize_param_key(orig))
    present = []
    absent = []
    for name in SERUM_CORE_NAMES:
        if normalize_param_key(name) in present_keys:
            present.append(name)
        else:
            absent.append(name)
    return {
        "catalog": "serum_core",
        "present": present,
        "absent": absent,
        "present_count": len(present),
        "absent_count": len(absent),
        "note": (
            "This instance's Configure list is incomplete by design (Live cap ~128). "
            "Set only names in present / get_device_parameters. Skip absent names; "
            "do not cache parameter indices between instances."
        ),
    }


def plugin_configure_note(class_name, configured, host_names):
    if not is_plugin_class(class_name):
        return None
    extra = ""
    try:
        configured = int(configured)
        host_names = int(host_names)
    except (TypeError, ValueError):
        configured = 0
        host_names = 0
    if host_names > configured:
        extra = " Host reports {0} names; {1} are configured.".format(host_names, configured)
    elif configured:
        extra = " {0} parameters are configured.".format(configured)
    return _CONFIGURE_NOTE + extra
