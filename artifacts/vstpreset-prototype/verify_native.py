"""Isolated public VST3 state acceptance probe, using local research host helpers.

Never attaches to the plugin running in Live. No private importer addresses.
"""
import ctypes as C
import json
from pathlib import Path
import sys

sys.path.insert(0, "H:/gitprojects/serum-preset-packager")
import native_serum as host
from build import read_vst, unpack_state

sys.stdout.reconfigure(encoding="utf-8")
path = Path(sys.argv[1])
_, chunks = read_vst(path.read_bytes())
dll = C.WinDLL(str(host.DEFAULT_PLUGIN))
if not dll.InitDll():
    raise RuntimeError("InitDll rejected")
dll.GetPluginFactory.restype = host.P
factory = dll.GetPluginFactory()
processor = host.P()
for i in range(host.call(factory, 4)):
    info = host.Info()
    if host.call(factory, 5, (host.I, host.P), (i, C.byref(info))) == 0 and info.category == b"Audio Module Class":
        cid = C.string_at(C.addressof(info), 16)
        status = host.call(factory, 6, (host.P, host.P, host.P),
                           (cid, host.uid("E831FF31-F2D5-4301-928E-BBEE25697802"), C.byref(processor)))
        if status != 0:
            raise RuntimeError("Cannot create processor")
        break
if not processor or host.call(processor, 3, (host.P,), (host.host.ptr,)) != 0:
    raise RuntimeError("Cannot initialize processor")
stream = host.Stream(chunks[b"Comp"])
status = host.call(processor, 12, (host.P,), (stream.ptr,))
result = {"processor_load_status": status}
if status != 0:
    raise RuntimeError(f"Processor rejected state: {status}")
stream = host.Stream()
if host.call(processor, 13, (host.P,), (stream.ptr,)) != 0:
    raise RuntimeError("Cannot read processor state")
_, readback = unpack_state(stream.io.getvalue())
_, expected = unpack_state(chunks[b"Comp"])
checks = []
for module in ("Env0", "Env1", "Global0", "Oscillator0", "Oscillator1", "Oscillator4", "VoiceFilter0"):
    values = expected[module]["plainParams"]
    if not isinstance(values, dict):
        continue
    actual = readback[module]["plainParams"]
    for key, value in values.items():
        got = actual.get(key) if isinstance(actual, dict) else None
        equal = (abs(value - got) < 1e-6 if isinstance(value, (int, float)) and isinstance(got, (int, float)) else got == value)
        checks.append({"module": module, "parameter": key, "expected": value, "actual": got, "equal": equal})
result.update(parameter_checks=checks, fx_order=[item["type"] for item in readback["FXRack0"]["FX"]])
present = [item for item in checks if item['actual'] is not None]
result['omitted_parameters_unverified'] = [item for item in checks if item['actual'] is None]
result['full_parameter_equality_verified'] = False
result['explicit_parameter_count'] = len(present)
result['passed'] = (all(item['equal'] for item in present)
                    and result['fx_order'] == [item['type'] for item in expected['FXRack0']['FX']])
result['controller_check'] = 'Not verified headlessly: setComponentState access violation with the minimal research host; use the real Ableton host.'
path.with_suffix('.native-check.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
print(json.dumps({key: value for key, value in result.items() if key != 'parameter_checks'}, indent=2))
print(f'Checked {len(checks)} native parameters')
# Release processor before unloading the plugin DLL.
host.call(processor, 4)
host.call(processor, 2)
host.call(factory, 2)
dll.ExitDll()
sys.exit(0 if result["passed"] else 1)
