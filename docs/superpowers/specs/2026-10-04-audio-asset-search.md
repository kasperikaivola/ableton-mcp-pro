# Recursive audio asset discovery

User wants agents to find presets/assets under deeply nested G:/AudioAssets.
Add read-only search_audio_assets with default root G:/AudioAssets, case-insensitive
wildcards *, ?, [] and recursive ** path segments. Patterns without slash match
filenames at any depth; slash patterns match root-relative paths. Return bounded
full paths, relative paths, sizes and Serum editor compatibility. Paginate results
by offset (best effort if library changes). Traverse no symlinks/junctions. Limit
entries examined and wall time; explicitly report incomplete scans/permission
errors, never claim an exhaustive total when stopped early. No content extraction,
asset writes, browser URI invention or indexing dependencies. Document preset
discovery before targeted reads, Init/template searches and legacy FXP limitation.

Focused checks cover nesting, recursive pattern matching, case, pagination,
scan limits and unsupported presets. One read-only real-library query verifies
the path; no preset edits or Live changes.
