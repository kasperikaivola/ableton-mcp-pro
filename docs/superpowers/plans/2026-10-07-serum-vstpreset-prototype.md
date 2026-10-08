# Serum VST3 preset loading prototype

Spec and plan (auto-accepted): test one same-build `.SerumPreset` converted into a
browser-loadable `.vstpreset`, using the user's existing host preset as structural
reference. Preserve source files and existing Live tracks. No production MCP
interface or general loading claim until the Live path is verified.

- [x] Package one fixture with observed Serum 2.0.16 component/controller schemas
  and VST3 class identity. Reject version mismatch and unmapped top-level fields.
- [x] Validate container and isolated plugin acceptance when possible.
- [x] Publish the output to Ableton User Library, discover its actual browser URI,
  load onto a newly created/named test track and read back device/parameters.
- [x] Report observed results, structural/live limits and remaining production work.

Experimental scripts and reports live in `artifacts/vstpreset-prototype`.

Results: Live browser loading succeeded on a new track (14), device 0 Serum 2;
29 selected live values matched source state. Original/template hashes unchanged.
Isolated processor state accepted; 32 explicitly serialized native values and FX
order matched. Native default omissions and a headless controller crash were
recorded, not interpreted as full equality. No audition or existing-device test.
Final self-review: same-build experimental scope, source guards and explicit
verification limits retained; no new public command surface or production tool.
