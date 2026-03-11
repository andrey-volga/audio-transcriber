# Tasks

## Planned improvements

- [ ] **Output folder for text files** — add `default_output` to config, so transcribed `.txt` files are saved to a fixed location instead of alongside the source audio.

- [ ] **Handling of processed audio files** — add post-transcription action config:
  - `after_transcription = "keep"` — do nothing (default)
  - `after_transcription = "delete"` — delete the source file after successful transcription
  - `after_transcription = "move"` — move the source file to a folder specified by `processed_folder`
