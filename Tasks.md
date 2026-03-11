# Tasks

## Planned improvements

- [ ] **Output folder for text files** — add `default_output` to config, so transcribed `.txt` files are saved to a fixed location instead of alongside the source audio.

- [ ] **Handling of processed audio files** — add post-transcription action config:
  - `after_transcription = "delete"` — delete the source file after successful transcription
  - `after_transcription = "move"` — move the source file to a folder specified by `processed_folder`
  
- [ ] Сделай и запусти daemon, который будет мониторить папку каждые 10 секунд (настраивается в конфиге) и если там будет появляться новый файл, то автоматически запускать транскрибацию.
- [ ] Обработанные аудио-файлы должны быть либо удалены, либо перемещены в папку [Done]
	- [ ] Путь к папке настривается в конфиге
- [ ] Готовые текстовые файлы должны лечь в папку ~/Obsidian/00. Inbox/Transcribes/ 
	- [ ] Формат имени файла: [YYYY-MM-DD Name]
- [ ] 
