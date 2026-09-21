"""Unit tests for plugin parameter matching (no Live process required)."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = ROOT / "AbletonMCP_Remote_Script"
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

import plugin_params as pp  # noqa: E402


def _p(index, name, original=None, display=None):
    return {
        "index": index,
        "name": name,
        "original_name": original,
        "display_value": display,
    }


SERUM = [
    _p(0, "Device On"),
    _p(98, "Filter 1 Freq", display="1.00 kHz"),
    _p(99, "Filter 1 Res"),
    _p(114, "Filter 2 Freq"),
    _p(31, "Macro 1"),
    _p(7, "A Level"),
]


class ClassifyDeviceTests(unittest.TestCase):
    def test_plugin_instrument_from_lom_type(self):
        self.assertEqual(
            pp.classify_device("PluginDevice", "Serum 2", 1, False, False),
            "instrument",
        )

    def test_plugin_audio_effect(self):
        self.assertEqual(
            pp.classify_device("AuPluginDevice", "FabFilter Pro-Q 3", 2, False, False),
            "audio_effect",
        )

    def test_rack_and_drum(self):
        self.assertEqual(pp.classify_device("InstrumentGroupDevice", "Rack", 1, False, True), "rack")
        self.assertEqual(pp.classify_device("DrumGroupDevice", "Kit", 1, True, True), "drum_machine")

    def test_native_operator(self):
        self.assertEqual(pp.classify_device("Operator", "Operator", 1, False, False), "instrument")


class FindParameterTests(unittest.TestCase):
    def test_exact_name(self):
        found = pp.find_parameter(SERUM, name="Filter 1 Freq")
        self.assertEqual(found["index"], 98)

    def test_case_insensitive(self):
        found = pp.find_parameter(SERUM, name="filter 1 freq")
        self.assertEqual(found["index"], 98)

    def test_alnum_collapse(self):
        found = pp.find_parameter(SERUM, name="Filter1Freq")
        self.assertEqual(found["index"], 98)

    def test_unique_substring(self):
        found = pp.find_parameter(SERUM, name="A Level")
        self.assertEqual(found["index"], 7)

    def test_ambiguous_filter_freq(self):
        with self.assertRaises(ValueError) as ctx:
            pp.find_parameter(SERUM, name="Freq")
        self.assertIn("ambiguous", str(ctx.exception).lower())

    def test_missing(self):
        with self.assertRaises(ValueError) as ctx:
            pp.find_parameter(SERUM, name="Wavetable Index")
        self.assertIn("not found", str(ctx.exception).lower())

    def test_by_index(self):
        found = pp.find_parameter(SERUM, index=31)
        self.assertEqual(found["name"], "Macro 1")

    def test_index_wins_over_name(self):
        found = pp.find_parameter(SERUM, index=99, name="Macro 1")
        self.assertEqual(found["name"], "Filter 1 Res")


class QueryFilterTests(unittest.TestCase):
    def test_filter_query(self):
        hits = pp.filter_parameters(SERUM, "filter 1")
        names = [p["name"] for p in hits]
        self.assertEqual(names, ["Filter 1 Freq", "Filter 1 Res"])

    def test_empty_query_keeps_all(self):
        self.assertEqual(len(pp.filter_parameters(SERUM, "")), len(SERUM))
        self.assertEqual(len(pp.filter_parameters(SERUM, None)), len(SERUM))

    def test_display_value_match(self):
        hits = pp.filter_parameters(SERUM, "1.00 kHz")
        self.assertEqual([p["name"] for p in hits], ["Filter 1 Freq"])


class GroupingTests(unittest.TestCase):
    def test_serum_osc_filter_env_macro(self):
        self.assertEqual(pp.parameter_group("A Level", "Serum 2"), "Oscillator A")
        self.assertEqual(pp.parameter_group("B WT Pos", "Serum 2"), "Oscillator B")
        self.assertEqual(pp.parameter_group("C Warp Mode", "Serum 2"), "Oscillator C")
        self.assertEqual(pp.parameter_group("Filter 1 Freq", "Serum 2"), "Filter 1")
        self.assertEqual(pp.parameter_group("Filter 2 On", "Serum 2"), "Filter 2")
        self.assertEqual(pp.parameter_group("Env 1 Attack", "Serum 2"), "Envelope 1")
        self.assertEqual(pp.parameter_group("LFO 1 Rate", "Serum 2"), "LFO 1")
        self.assertEqual(pp.parameter_group("Macro 3", "Serum 2"), "Macros")
        self.assertEqual(pp.parameter_group("A>Filter Balance", "Serum 2"), "Filter routing")
        self.assertEqual(pp.parameter_group("Sub Osc>Filter Balance", "Serum 2"), "Filter routing")
        self.assertEqual(pp.parameter_group("Main Vol", "Serum 2"), "Main")
        self.assertEqual(pp.parameter_group("Sub Level", "Serum 2"), "Sub oscillator")
        self.assertEqual(pp.parameter_group("Porta Time", "Serum 2"), "Voice")
        self.assertEqual(pp.parameter_group("Device On", "Serum 2"), "Device")

    def test_attach_groups_orders_and_annotates(self):
        params = [
            _p(0, "Device On"),
            _p(7, "A Level"),
            _p(98, "Filter 1 Freq"),
            _p(99, "Filter 1 Res"),
            _p(31, "Macro 1"),
        ]
        annotated, groups = pp.attach_groups(params, "Serum 2")
        self.assertEqual([p["group"] for p in annotated], [
            "Device", "Oscillator A", "Filter 1", "Filter 1", "Macros",
        ])
        names = [g["name"] for g in groups]
        self.assertEqual(names, ["Device", "Oscillator A", "Filter 1", "Macros"])
        filt = [g for g in groups if g["name"] == "Filter 1"][0]
        self.assertEqual(filt["count"], 2)
        self.assertEqual([p["name"] for p in filt["parameters"]], ["Filter 1 Freq", "Filter 1 Res"])

    def test_query_matches_group_name(self):
        annotated, _groups = pp.attach_groups(SERUM, "Serum 2")
        hits = pp.filter_parameters(annotated, "oscillator a")
        self.assertEqual([p["name"] for p in hits], ["A Level"])

    def test_exact_group_query_does_not_match_unrelated_names(self):
        params = [
            _p(105, "Key"),
            _p(106, "Scale"),
            _p(121, "Porta Scaled"),
        ]
        annotated, _groups = pp.attach_groups(params, "Serum 2")
        hits = pp.filter_parameters(annotated, "Scale")
        self.assertEqual([p["name"] for p in hits], ["Key", "Scale"])

    def test_key_scale_swing_groups(self):
        self.assertEqual(pp.parameter_group("Key", "Serum 2"), "Scale")
        self.assertEqual(pp.parameter_group("Scale", "Serum 2"), "Scale")
        self.assertEqual(pp.parameter_group("Swing", "Serum 2"), "Groove")


class CoverageTests(unittest.TestCase):
    def test_partial_serum_mapping_reports_absent_core(self):
        report = pp.mapping_coverage(SERUM, device_name="Serum 2")
        self.assertEqual(report["catalog"], "serum_core")
        self.assertIn("Filter 1 Freq", report["present"])
        self.assertIn("A Level", report["present"])
        self.assertIn("Main Vol", report["absent"])
        self.assertIn("C Level", report["absent"])
        self.assertGreater(report["absent_count"], 0)

    def test_non_serum_has_no_catalog(self):
        self.assertIsNone(pp.mapping_coverage(SERUM, device_name="Operator"))

    def test_try_find_missing_is_none(self):
        self.assertIsNone(pp.try_find_parameter(SERUM, name="C Level"))
        self.assertEqual(pp.try_find_parameter(SERUM, name="Macro 1")["index"], 31)

    def test_missing_error_mentions_configure(self):
        with self.assertRaises(ValueError) as ctx:
            pp.find_parameter(SERUM, name="C Level")
        msg = str(ctx.exception).lower()
        self.assertIn("not found", msg)
        self.assertIn("configure", msg)


class ConfigureNoteTests(unittest.TestCase):
    def test_plugin_note_mentions_configure_and_cap(self):
        note = pp.plugin_configure_note("PluginDevice", configured=125, host_names=400)
        self.assertIn("Configure", note)
        self.assertIn("128", note)
        self.assertIn("Default Configuration", note)

    def test_native_device_has_no_note(self):
        self.assertIsNone(pp.plugin_configure_note("Operator", configured=20, host_names=0))


if __name__ == "__main__":
    unittest.main()
