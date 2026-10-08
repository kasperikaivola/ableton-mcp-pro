"""Static public-surface tests for the three Ableton MCP backends."""

from __future__ import annotations

import ast
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MCP_SERVER = ROOT / "MCP_Server"
REMOTE_SCRIPT = ROOT / "AbletonMCP_Remote_Script"
MAX_CODE = ROOT / "MaxForLive" / "code"


# Captured from git show HEAD:MCP_Server/server.py at baseline commit 167016a.
EXPECTED_MCP_TOOLS = frozenset(
    {
        "add_macro",
        "add_notes_to_clip",
        "add_warp_marker",
        "apply_groove",
        "apply_note_modifications",
        "batch_set_device_parameters",
        "capture_and_insert_scene",
        "capture_midi",
        "clear_clip_envelope",
        "clear_clip_groove",
        "continue_playing",
        "convert_clip_time",
        "create_arrangement_audio_clip",
        "create_arrangement_audio_clips_batch",
        "create_arrangement_midi_clip",
        "create_audio_track",
        "create_clip",
        "create_midi_track",
        "create_return_track",
        "create_scene",
        "crop_clip",
        "delete_arrangement_clip",
        "delete_clip",
        "delete_device",
        "delete_macro_variation",
        "delete_return_track",
        "delete_scene",
        "delete_track",
        "delete_warp_marker",
        "duplicate_clip",
        "duplicate_clip_loop",
        "duplicate_clip_to_arrangement",
        "duplicate_region",
        "duplicate_scene",
        "duplicate_track",
        "fire_clip",
        "fire_scene",
        "get_application_info",
        "get_arrangement_clip_notes",
        "get_arrangement_clips",
        "get_arrangement_info",
        "get_browser_items_at_path",
        "get_browser_tree",
        "get_clip_envelope",
        "get_clip_info",
        "get_clip_notes",
        "get_cue_points",
        "get_device_parameters",
        "get_device_sidechain",
        "get_drum_pads",
        "get_full_arrangement",
        "get_groove_pool",
        "get_rack_chains",
        "get_rack_macros",
        "get_session_info",
        "get_synth_sound_design_guide",
        "get_serum_preset_info",
        "read_serum_preset",
        "search_serum_preset",
        "search_audio_assets",
        "edit_serum_preset",
        "convert_serum_preset",
        "compare_serum_presets",
        "get_simpler_sample",
        "get_track_info",
        "get_track_routing",
        "get_warp_markers",
        "generate_midi_continuation",
        "insert_device",
        "insert_rack_chain",
        "jump_by",
        "jump_to_cue",
        "load_drum_kit",
        "load_drum_pad_sample",
        "load_instrument_or_effect",
        "move_device",
        "move_warp_marker",
        "play_arrangement",
        "press_current_dialog_button",
        "quantize_clip",
        "quantize_pitch",
        "randomize_macros",
        "re_enable_automation",
        "recall_macro_variation",
        "record_arrangement",
        "redo",
        "remove_macro",
        "remove_notes",
        "replace_simpler_sample",
        "resample_master",
        "set_arrangement_loop",
        "set_arrangement_overdub",
        "set_back_to_arranger",
        "set_chain_mixer",
        "set_clip_color",
        "set_clip_envelope",
        "set_clip_gain",
        "set_clip_launch",
        "set_clip_loop",
        "set_clip_markers",
        "set_clip_muted",
        "set_clip_name",
        "set_clip_pitch",
        "set_clip_ram_mode",
        "set_clip_signature",
        "set_clip_warp_mode",
        "set_clip_warping",
        "set_count_in_duration",
        "set_crossfade_assign",
        "set_crossfader",
        "set_cue_volume",
        "set_device_enabled",
        "set_device_parameter",
        "set_device_sidechain",
        "set_exclusive_arm",
        "set_groove_amount",
        "set_metronome",
        "set_plugin_preset",
        "set_punch",
        "set_record_mode",
        "set_scene_color",
        "set_scene_name",
        "set_scene_signature",
        "set_scene_tempo",
        "set_send_level",
        "set_session_automation_record",
        "set_session_record",
        "set_simpler_sample_window",
        "set_song_scale",
        "set_song_time",
        "set_tempo",
        "set_time_signature",
        "set_track_arm",
        "set_track_color",
        "set_track_input_routing",
        "set_track_monitoring",
        "set_track_mute",
        "set_track_name",
        "set_track_output_routing",
        "set_track_panning",
        "set_track_solo",
        "set_track_volume",
        "show_view",
        "start_playback",
        "stop_all_clips",
        "stop_clip",
        "stop_playback",
        "store_macro_variation",
        "tap_tempo",
        "toggle_cue",
        "undo",
    }
)


# Captured from git show HEAD:AbletonMCP_Remote_Script/__init__.py at baseline.
EXPECTED_REMOTE_COMMANDS = frozenset(
    {
        "add_macro",
        "add_notes_to_clip",
        "add_warp_marker",
        "apply_groove",
        "apply_note_modifications",
        "batch_set_device_parameters",
        "capture_and_insert_scene",
        "capture_midi",
        "clear_clip_envelope",
        "clear_clip_groove",
        "continue_playing",
        "convert_clip_time",
        "create_arrangement_audio_clip",
        "create_arrangement_audio_clips_batch",
        "create_arrangement_midi_clip",
        "create_audio_track",
        "create_clip",
        "create_midi_track",
        "create_return_track",
        "create_scene",
        "crop_clip",
        "delete_arrangement_clip",
        "delete_clip",
        "delete_device",
        "delete_macro_variation",
        "delete_return_track",
        "delete_scene",
        "delete_track",
        "delete_warp_marker",
        "duplicate_clip",
        "duplicate_clip_loop",
        "duplicate_clip_to_arrangement",
        "duplicate_region",
        "duplicate_scene",
        "duplicate_track",
        "fire_clip",
        "fire_scene",
        "get_application_info",
        "get_arrangement_clip_notes",
        "get_arrangement_clips",
        "get_arrangement_info",
        "get_browser_categories",
        "get_browser_item",
        "get_browser_items",
        "get_browser_items_at_path",
        "get_browser_tree",
        "get_clip_envelope",
        "get_clip_info",
        "get_clip_notes",
        "get_cue_points",
        "get_device_parameters",
        "get_device_sidechain",
        "get_drum_pads",
        "get_full_arrangement",
        "get_groove_pool",
        "get_rack_chains",
        "get_rack_macros",
        "get_session_info",
        "get_simpler_sample",
        "get_track_info",
        "get_track_routing",
        "get_warp_markers",
        "insert_device",
        "insert_rack_chain",
        "jump_by",
        "jump_to_cue",
        "load_browser_item",
        "load_drum_pad_sample",
        "load_instrument_or_effect",
        "move_device",
        "move_warp_marker",
        "play_arrangement",
        "press_current_dialog_button",
        "quantize_clip",
        "quantize_pitch",
        "randomize_macros",
        "re_enable_automation",
        "recall_macro_variation",
        "record_arrangement",
        "redo",
        "remove_macro",
        "remove_notes",
        "replace_simpler_sample",
        "resample_master",
        "set_arrangement_loop",
        "set_arrangement_overdub",
        "set_back_to_arranger",
        "set_chain_mixer",
        "set_clip_color",
        "set_clip_envelope",
        "set_clip_gain",
        "set_clip_launch",
        "set_clip_loop",
        "set_clip_markers",
        "set_clip_muted",
        "set_clip_name",
        "set_clip_pitch",
        "set_clip_ram_mode",
        "set_clip_signature",
        "set_clip_warp_mode",
        "set_clip_warping",
        "set_count_in_duration",
        "set_crossfade_assign",
        "set_crossfader",
        "set_cue_volume",
        "set_device_enabled",
        "set_device_parameter",
        "set_device_sidechain",
        "set_exclusive_arm",
        "set_groove_amount",
        "set_metronome",
        "set_plugin_preset",
        "set_punch",
        "set_record_mode",
        "set_scene_color",
        "set_scene_name",
        "set_scene_signature",
        "set_scene_tempo",
        "set_send_level",
        "set_session_automation_record",
        "set_session_record",
        "set_simpler_sample_window",
        "set_song_scale",
        "set_song_time",
        "set_tempo",
        "set_time_signature",
        "set_track_arm",
        "set_track_color",
        "set_track_input_routing",
        "set_track_monitoring",
        "set_track_mute",
        "set_track_name",
        "set_track_output_routing",
        "set_track_panning",
        "set_track_solo",
        "set_track_volume",
        "show_view",
        "start_playback",
        "stop_all_clips",
        "stop_clip",
        "stop_playback",
        "store_macro_variation",
        "tap_tempo",
        "toggle_cue",
        "undo",
    }
)


# Captured from git show HEAD:MaxForLive/code/lom-handler.js at baseline.
EXPECTED_MAX_COMMANDS = frozenset(
    {
        "add_macro",
        "add_notes_to_clip",
        "add_warp_marker",
        "apply_groove",
        "apply_note_modifications",
        "batch_set_device_parameters",
        "capture_and_insert_scene",
        "capture_midi",
        "clear_clip_envelope",
        "clear_clip_groove",
        "continue_playing",
        "convert_clip_time",
        "create_arrangement_audio_clip",
        "create_arrangement_midi_clip",
        "create_audio_clip",
        "create_audio_track",
        "create_clip",
        "create_midi_track",
        "create_scene",
        "crop_clip",
        "delete_arrangement_clip",
        "delete_clip",
        "delete_device",
        "delete_macro_variation",
        "delete_scene",
        "delete_track",
        "delete_warp_marker",
        "duplicate_clip",
        "duplicate_clip_to_arrangement",
        "duplicate_scene",
        "duplicate_track",
        "fire_clip",
        "fire_scene",
        "get_application_info",
        "get_arrangement_clip_notes",
        "get_arrangement_clips",
        "get_arrangement_info",
        "get_browser_items_at_path",
        "get_browser_tree",
        "get_clip_envelope",
        "get_clip_notes",
        "get_cue_points",
        "get_device_parameters",
        "get_device_sidechain",
        "get_full_arrangement",
        "get_groove_pool",
        "get_rack_chains",
        "get_rack_macros",
        "get_session_info",
        "get_simpler_sample",
        "get_track_info",
        "get_track_routing",
        "get_warp_markers",
        "insert_device",
        "insert_rack_chain",
        "jump_by",
        "jump_to_cue",
        "load_browser_item",
        "load_drum_pad_sample",
        "load_instrument_or_effect",
        "move_device",
        "move_warp_marker",
        "ping",
        "play_arrangement",
        "press_current_dialog_button",
        "quantize_pitch",
        "randomize_macros",
        "re_enable_automation",
        "recall_macro_variation",
        "record_arrangement",
        "redo",
        "remove_macro",
        "replace_simpler_sample",
        "set_arrangement_loop",
        "set_arrangement_overdub",
        "set_back_to_arranger",
        "set_chain_mixer",
        "set_clip_color",
        "set_clip_envelope",
        "set_clip_launch",
        "set_clip_loop",
        "set_clip_markers",
        "set_clip_muted",
        "set_clip_name",
        "set_clip_ram_mode",
        "set_clip_signature",
        "set_count_in_duration",
        "set_crossfade_assign",
        "set_crossfader",
        "set_cue_volume",
        "set_device_parameter",
        "set_device_sidechain",
        "set_exclusive_arm",
        "set_groove_amount",
        "set_metronome",
        "set_plugin_preset",
        "set_punch",
        "set_record_mode",
        "set_scene_color",
        "set_scene_name",
        "set_scene_signature",
        "set_scene_tempo",
        "set_send_level",
        "set_session_automation_record",
        "set_session_record",
        "set_simpler_sample_window",
        "set_song_scale",
        "set_song_time",
        "set_tempo",
        "set_time_signature",
        "set_track_arm",
        "set_track_color",
        "set_track_input_routing",
        "set_track_monitoring",
        "set_track_mute",
        "set_track_name",
        "set_track_output_routing",
        "set_track_panning",
        "set_track_solo",
        "set_track_volume",
        "show_view",
        "start_playback",
        "stop_clip",
        "stop_playback",
        "store_macro_variation",
        "tap_tempo",
        "toggle_cue",
        "undo",
    }
)


def _python_sources(root):
    return sorted(
        path
        for path in root.rglob("*.py")
        if "__pycache__" not in path.parts
    )


def _string_constant(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.Str):
        return node.s
    return None


def _is_mcp_tool_decorator(decorator):
    if isinstance(decorator, ast.Call):
        decorator = decorator.func
    return (
        isinstance(decorator, ast.Attribute)
        and decorator.attr == "tool"
        and isinstance(decorator.value, ast.Name)
        and decorator.value.id == "mcp"
    )


def discover_mcp_tools():
    names = set()
    for path in _python_sources(MCP_SERVER):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and any(
                _is_mcp_tool_decorator(decorator) for decorator in node.decorator_list
            ):
                names.add(node.name)
    return names


_COMMAND_VARIABLES = {"command_type", "command_name", "cmd_type"}


def _command_values(compare):
    if not isinstance(compare, ast.Compare):
        return set()
    if len(compare.ops) != 1:
        return set()
    if not isinstance(compare.left, ast.Name) or compare.left.id not in _COMMAND_VARIABLES:
        return set()

    operator = compare.ops[0]
    comparator = compare.comparators[0]
    if isinstance(operator, ast.Eq):
        value = _string_constant(comparator)
        return {value} if value is not None else set()
    if isinstance(operator, ast.In) and isinstance(comparator, (ast.List, ast.Tuple, ast.Set)):
        return {
            value
            for value in (_string_constant(element) for element in comparator.elts)
            if value is not None
        }
    return set()


def _self_method_calls(node):
    nodes = (node,) if isinstance(node, ast.AST) else node
    return {
        call.func.attr
        for item in nodes
        for call in ast.walk(item)
        if isinstance(call, ast.Call)
        and isinstance(call.func, ast.Attribute)
        and isinstance(call.func.value, ast.Name)
        and call.func.value.id == "self"
    }


def _class_definitions():
    definitions = {}
    for path in _python_sources(REMOTE_SCRIPT):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                definitions[node.name] = node
    return definitions


def discover_ableton_method_names():
    definitions = _class_definitions()
    ableton_class = definitions["AbletonMCP"]
    pending = [base.id for base in ableton_class.bases if isinstance(base, ast.Name)]
    methods = set()

    while pending:
        class_name = pending.pop()
        class_node = definitions.get(class_name)
        if class_node is None:
            continue
        methods.update(
            node.name
            for node in class_node.body
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        )
        pending.extend(
            base.id for base in class_node.bases if isinstance(base, ast.Name)
        )

    methods.update(
        node.name
        for node in ableton_class.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    )
    return methods


def test_application_info_dispatch_uses_main_thread_queue():
    source = REMOTE_SCRIPT.joinpath("control_surface.py")
    tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
    process_command = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "_process_command"
    )

    queued_branches = [
        node
        for node in ast.walk(process_command)
        if isinstance(node, ast.If)
        and "get_application_info" in _command_values(node.test)
        and "_get_application_info" in _self_method_calls(node.body)
        and "schedule_message" in _self_method_calls(node.body)
        and any(
            isinstance(child, ast.FunctionDef) and child.name == "main_thread_task"
            for child in node.body
        )
    ]

    assert queued_branches, "get_application_info must execute on Live's main thread"


def discover_read_only_dispatch_handlers():
    control_surface = REMOTE_SCRIPT / "control_surface.py"
    tree = ast.parse(
        control_surface.read_text(encoding="utf-8"), filename=str(control_surface)
    )
    process_command = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name == "_process_command"
    )
    dispatch = next(
        node
        for node in ast.walk(process_command)
        if isinstance(node, ast.If)
        and _command_values(node.test)
        and any(isinstance(op, ast.In) for op in node.test.ops)
    )

    handlers = set()
    branch = dispatch
    while isinstance(branch, ast.If):
        if _command_values(branch.test) and not any(
            isinstance(op, ast.In) for op in branch.test.ops
        ):
            handlers.update(_self_method_calls(branch.body))
        branch = branch.orelse[0] if len(branch.orelse) == 1 else None
    return handlers


def discover_remote_commands():
    names = set()
    for path in _python_sources(REMOTE_SCRIPT):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                names.update(_command_values(node))
    return names


_MAX_CASE = re.compile(r"(?m)^\s*case\s+[\"']([^\"']+)[\"']\s*:")


def discover_max_commands():
    names = set()
    for path in sorted(MAX_CODE.glob("*.js")):
        names.update(_MAX_CASE.findall(path.read_text(encoding="utf-8")))
    return names


def test_mcp_tool_surface_matches_baseline():
    assert discover_mcp_tools() == EXPECTED_MCP_TOOLS


def test_remote_command_surface_matches_baseline():
    assert discover_remote_commands() == EXPECTED_REMOTE_COMMANDS


def test_read_only_dispatch_handlers_are_supplied_by_ableton_mcp():
    handlers = discover_read_only_dispatch_handlers()
    assert {"_get_browser_categories", "_get_browser_items"} <= handlers
    assert handlers <= discover_ableton_method_names()


def test_max_command_surface_matches_baseline():
    assert discover_max_commands() == EXPECTED_MAX_COMMANDS
