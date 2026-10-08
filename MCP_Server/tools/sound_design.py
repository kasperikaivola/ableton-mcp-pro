"""Offline sound-design references; these tools never connect to Live."""

import json
import re
from importlib.resources import files

from mcp.server.fastmcp import Context

from ..runtime import mcp


_GUIDES = {"overview": "overview.md", "serum2": "serum2.md", "omnisphere": "omnisphere.md",
           "serum-presets": "serum-presets.md"}
_ALIASES = {
    "serum": "serum2", "serum 2": "serum2", "serum-2": "serum2",
    "omnisphere 2": "omnisphere", "omnisphere2": "omnisphere",
    "omnisphere 3": "omnisphere", "omnisphere3": "omnisphere",
}
_INSTRUCTIONS = (
    "Read overview/workflow first, then the selected synth's identity and relevant "
    "control sections (or all). For new Serum 2 presets, read serum-presets/workflow, "
    "new-preset-design and module-editing; create and write a separate .SerumPreset "
    "with substantial style-defining edits across sources, filters, envelopes, "
    "modulation, FX and voicing. Missing Configure controls do not block offline "
    "creation; do not stop at a recipe or dry-run. For live-instance edits inspect "
    "the session and unfiltered get_device_parameters; file-only creation needs no "
    "Live connection. A request for suggestions alone "
    "is read-only, but 'make this preset faster/darker/bouncy' authorizes edits: "
    "read serum-presets/existing-preset-edits, unpack the identified existing "
    ".SerumPreset to complete disk JSON, edit a separate JSON, repack a separate "
    "preset and compare decoded state. Preserve the original and unrelated settings. "
    "A request for suggestions alone "
    "does not authorize patch edits. Use existing Live tools for authorized creation, "
    "loading and verified writes; this guide does not apply settings. Always include "
    "a '<Synth> — manual settings' section in the final chat with every intended "
    "unapplied setting, UI location, desired value/units and 'not applied — set manually'. "
    "For Omnisphere identify version, Part and Layer. Unseen settings and unavailable "
    "asset names remain unknown/unverified; recipe values are proposals, not readback. "
    "Group decoded-verified file settings as encoded in output; not loaded, with a "
    "load/verification step instead of redundant manual recreation. Keep true "
    "unencoded gaps explicit; file-only requests have no track/device prerequisite."
    " Read serum-presets/complete-state-recipes for full FX/matrix/wavetable and "
    "other decoded-state edits. edit_serum_preset copy operations transfer complete "
    "guarded reference subtrees/assets without using truncated chat previews. "
    "Pending live readback does not mean those decoded file edits are unavailable."
)


def _sections(document: str) -> dict[str, tuple[str, str]]:
    headings = list(re.finditer(r"^## (.+)$", document, re.MULTILINE))
    result = {}
    for index, heading in enumerate(headings):
        title = heading.group(1).strip()
        key = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-")
        end = headings[index + 1].start() if index + 1 < len(headings) else len(document)
        result[key] = (title, document[heading.start():end].strip())
    return result


@mcp.tool()
def get_synth_sound_design_guide(
    ctx: Context, synth: str = "overview", section: str = "index"
) -> str:
    """Read offline Serum 2 / Omnisphere control manuals and sound-design workflows.

    Use for adding a new synth sound, making a mystical FX/pad/bass/lead, or
    suggesting improvements to a bland existing synth track. First read
    synth='overview', section='workflow'; then retrieve the chosen synth's
    control reference and recipes. This tool only returns guidance, never edits
    Live or claims it can see/hear unmapped plug-in settings.

    New Serum 2 preset requests: read serum-presets/workflow, new-preset-design
    and module-editing, then use the offline preset tools to write a substantially
    designed separate .SerumPreset. Cover wavetable/source selection, sub/noise,
    filters/routing, multiple envelopes/LFOs, matrix/performance, ordered/repeated
    FX and voicing. Missing Configure controls are not an offline editing blocker.
    File-only creation does not require Live; file edits are not live application.

    Existing Serum preset transformations ('make it faster/darker/bouncy', etc.)
    authorize actual edits, not just suggestions. Read serum-presets section
    existing-preset-edits: identify the current source, unpack with
    convert_serum_preset to complete JSON, edit separate JSON, repack a separate
    .SerumPreset and compare decoded changes. Preserve originals/unrelated state.

    synth: overview, serum2, omnisphere, serum-presets (offline file editing).
    section: index lists section IDs, all reads the complete guide, or use an ID
    from index. Omnisphere is version-aware; aliases do not verify installed version.
    Always give detailed final-chat manual settings for every unapplied intended
    control, including sources, modulation and FX. Keep proposals separate from
    verified parameter writes. Suggestion-only requests must preserve the patch.
    """
    requested = synth.strip().lower()
    selected = _ALIASES.get(requested, requested)
    if selected not in _GUIDES:
        return json.dumps({"error": "Unknown synth. Choose an available synth.",
                           "available_synths": list(_GUIDES)})
    try:
        document = files("MCP_Server.synth_guides").joinpath(_GUIDES[selected]).read_text(
            encoding="utf-8"
        )
    except (OSError, ModuleNotFoundError) as exc:
        return json.dumps({"error": f"Bundled guide unavailable: {exc}", "synth": selected})
    sections = _sections(document)
    section = section.strip().lower()
    result = {"synth": selected, "instructions": _INSTRUCTIONS,
              "available_synths": list(_GUIDES),
              "sections": {key: item[0] for key, item in sections.items()}}
    if section == "all":
        result.update(section="all", content=document)
    elif section == "index":
        result["section"] = "index"
    elif section in sections:
        result.update(section=section, content=sections[section][1])
    else:
        result["error"] = "Unknown section. Use index, all, or an ID from sections."
    return json.dumps(result, indent=2, ensure_ascii=False)
