# MCP issues

Faults seen when driving Live through the MCP / Remote Script (TCP **9877**). Working behaviour does not belong here. Grok AbletonMCP must use `ABLETON_PORT=9877`; **9878** is Max for Live and is closed unless that device is on a track.

## `clear_clip_groove`

`apply_groove` assigns a Groove Pool entry. Clear does not.

Live rejects `clip.groove = None` (`NoneType` vs `TPyHandle<AAbstractGroove>`). `0` and `False` fail the same way (`None.None(Clip, bool)`). Copying `.groove` from a newly created MIDI clip does not help: those clips already report `has_groove: true` on this Live 12 build, so there is no empty handle to copy.

Max can `clip.set("groove", "id", 0)`. That null handle is not available from the Python Remote Script.

## `set_count_in_duration` / `set_exclusive_arm`

Both tools exist and fail with `property of 'Song' object has no setter` on this Live 12 build. `set_punch` does set.

## Arrangement `set_clip_envelope`

Session clip envelopes write and read. Arrangement clips raise: automation lives on the track, not the clip. `get_clip_envelope` on an arrangement clip returns `has_envelope: false` plus that note. Not a session-clip bug.

## Warp shadow markers

User-added markers: `add_warp_marker` / `move_warp_marker` / `delete_warp_marker` work (`Live.Clip.WarpMarker(sample_time_seconds, beat_time)`).

Live’s automatic start/end (“shadow”) markers: move returns `The shadow marker can't be moved.`; delete returns `The specified warp marker doesn't exist`.

## Startup dialogs and port 9877 binding

After a Live quit that is not clean, Live may show crash-recovery or Save Untitled. Until that dialog is dismissed, the Control Surface does not bind **9877** and MCP `get_session_info` fails with “Could not connect to Ableton” even though the Live process is running.

`press_current_dialog_button` depends on the Remote Script socket already being bound. It cannot by itself dismiss a startup dialog that prevents port **9877** from opening, so this startup fault remains outside that command's reach.

## Connection / reload

If Grok AbletonMCP is started with `ABLETON_PORT=9878` and no Max device is loaded, every tool fails the same way while 9877 is healthy.

A stale MCP socket after Live restart needs an AbletonMCP process reload; `live_client` on 9877 can still work.
