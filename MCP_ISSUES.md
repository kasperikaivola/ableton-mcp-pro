# MCP issues

Open faults and API limits checked against Live 12.4 through the Ableton MCP on 2026-10-01, unless noted otherwise.

## `clear_clip_groove`

After assigning a Groove Pool groove to a temporary MIDI clip, `clear_clip_groove` still failed. Live reported that the clip remained grooved and rejected a null `TPyHandle<AAbstractGroove>` from the Python Remote Script. The Max for Live path can set the groove ID to `0`, but that null handle is not available through the Python assignment used here.

## `set_count_in_duration` and `set_exclusive_arm`

Both tools still fail with `property of 'Song' object has no setter` on Live 12.4. Calls with `bars=1` and `on=false` reproduced the errors.

## Arrangement `set_clip_envelope`

Setting an envelope on a temporary arrangement MIDI clip still fails because arrangement automation belongs to the track and is not exposed by this clip-envelope API. `get_clip_envelope` returns `has_envelope: false` with that explanation. This is a public Live Object Model limit; the session-clip envelope API is separate.

## Automatic warp shadow markers

On a temporary arrangement audio clip, moving its automatic end marker returned `The shadow marker can't be moved.` Deleting that marker returned `The shadow marker can't be deleted.` The ordinary start marker in this clip could be moved and deleted, so this issue is specific to shadow markers.

## Startup dialogs before the Remote Script binds

If Live shows a startup dialog before the Remote Script binds TCP port **9877**, the MCP cannot call `press_current_dialog_button` to dismiss it. No blocking startup dialog was present during this check, so the startup failure was not reproduced. The command requires an already connected Remote Script socket.

## First MCP request after a Live restart

Earlier Live restarts produced a single `WinError 10054` on the persistent MCP connection; a following request reconnected. This was not retested because the current Set was left open. The first-request failure remains unverified on the current session.
