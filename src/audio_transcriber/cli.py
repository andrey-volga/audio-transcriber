import threading
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from audio_transcriber import config as cfg
from audio_transcriber.transcriber import transcribe
from audio_transcriber.utils import collect_audio_files, handle_processed_file, output_path

app = typer.Typer(
    name="transcribe",
    help="Локальная транскрибация аудио/видео-файлов в текст (Whisper, CPU).",
    add_completion=False,
)
config_app = typer.Typer(
    name="transcribe-config",
    help="Управление конфигурацией audio-transcriber.",
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True, style="bold red")


@config_app.command("set-source")
def config_set_source(
    path: Path = typer.Argument(..., help="Путь к папке с аудио-файлами по умолчанию."),
) -> None:
    """Установить папку с аудио по умолчанию."""
    if not path.is_dir():
        err_console.print(f"Ошибка: '{path}' не является директорией.")
        raise typer.Exit(1)
    data = cfg.load()
    data["default_source"] = str(path.resolve())
    cfg.save(data)
    console.print(f"[green]✓[/green] Дефолтная папка установлена: [cyan]{path.resolve()}[/cyan]")


@config_app.command("show")
def config_show() -> None:
    """Показать текущую конфигурацию."""
    data = cfg.load()
    if not data:
        console.print("[dim]Конфигурация пуста. Файл:[/dim] " + str(cfg.CONFIG_PATH))
        return
    console.print(f"[bold]Конфиг:[/bold] {cfg.CONFIG_PATH}")
    for key, value in data.items():
        console.print(f"  {key} = {value}")


@app.command()
def main(
    source: Optional[Path] = typer.Argument(
        None,
        help="Путь к аудио-файлу или директории. Если не указан — берётся из конфига.",
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Директория для сохранения MD-файлов (по умолчанию — из конфига или рядом с исходным файлом).",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model", "-m",
        help="Размер модели Whisper: tiny, base, small, medium, large. По умолчанию из конфига или base.",
    ),
    language: str = typer.Option(
        "ru",
        "--lang", "-l",
        help="Код языка транскрибации (ru, en, ...).",
    ),
) -> None:
    """Транскрибирует аудио/видео-файл(ы) в TXT."""
    if model is None:
        model = cfg.get_default_model() or "base"

    if source is None:
        source = cfg.get_default_source()
        if source is None:
            err_console.print(
                "Ошибка: не указан source и не задана дефолтная папка. "
                "Используй: transcribe-config set-source /path/to/folder"
            )
            raise typer.Exit(1)
        console.print(f"[dim]Источник из конфига: {source}[/dim]")

    if not source.exists():
        err_console.print(f"Ошибка: путь не найден: '{source}'")
        raise typer.Exit(1)

    if output_dir is None:
        output_dir = cfg.get_default_output()

    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    try:
        files = collect_audio_files(source)
    except (ValueError, FileNotFoundError) as e:
        err_console.print(f"Ошибка: {e}")
        raise typer.Exit(1)

    action = cfg.get_after_transcription()
    processed_folder = cfg.get_processed_folder()

    console.print(f"[bold]Найдено файлов:[/bold] {len(files)}")
    console.print(f"[bold]Модель:[/bold] whisper-{model}  |  [bold]Язык:[/bold] {language}\n")

    success, failed = 0, 0

    for audio_file in files:
        out = output_path(audio_file, output_dir)
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            transient=True,
            console=console,
        ) as progress:
            progress.add_task(f"Транскрибирую [cyan]{audio_file.name}[/cyan]…")
            try:
                text = transcribe(audio_file, model_name=model, language=language)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(text, encoding="utf-8")
                console.print(f"[green]✓[/green] {audio_file.name} → [dim]{out}[/dim]")
                handle_processed_file(audio_file, action, processed_folder)
                success += 1
            except Exception as e:
                err_console.print(f"✗ {audio_file.name}: {e}")
                failed += 1

    console.print(f"\nГотово: [green]{success}[/green] успешно, [red]{failed}[/red] с ошибками.")
    if failed:
        raise typer.Exit(1)


@app.command()
def watch(
    source: Optional[Path] = typer.Argument(
        None,
        help="Папка для мониторинга. Если не указана — берётся из конфига.",
    ),
    model: Optional[str] = typer.Option(
        None,
        "--model", "-m",
        help="Размер модели Whisper: tiny, base, small, medium, large.",
    ),
    language: str = typer.Option(
        "ru",
        "--lang", "-l",
        help="Код языка транскрибации (ru, en, ...).",
    ),
) -> None:
    """Мониторит папку и автоматически транскрибирует новые файлы."""
    if model is None:
        model = cfg.get_default_model() or "base"

    if source is None:
        source = cfg.get_default_source()
        if source is None:
            err_console.print(
                "Ошибка: не задана папка для мониторинга. "
                "Укажи путь или задай default_source в конфиге."
            )
            raise typer.Exit(1)

    output_dir = cfg.get_default_output()
    interval = cfg.get_monitor_interval()
    action = cfg.get_after_transcription()
    processed_folder = cfg.get_processed_folder()

    console.print(f"Мониторинг: [cyan]{source}[/cyan] (каждые {interval} сек)")
    console.print("[dim]Ctrl+C для остановки[/dim]\n")

    seen: set[Path] = set()

    try:
        while True:
            try:
                files = collect_audio_files(source)
            except (ValueError, FileNotFoundError):
                files = []

            new_files = [f for f in files if f not in seen]
            for audio_file in new_files:
                seen.add(audio_file)
                out = output_path(audio_file, output_dir)
                try:
                    result: dict = {}

                    def _run(af=audio_file, m=model, lang=language, r=result):
                        try:
                            r["text"] = transcribe(af, model_name=m, language=lang)
                        except Exception as exc:
                            r["error"] = exc

                    t = threading.Thread(target=_run, daemon=True)
                    t.start()
                    while t.is_alive():
                        t.join(timeout=0.5)

                    if "error" in result:
                        raise result["error"]

                    out.parent.mkdir(parents=True, exist_ok=True)
                    out.write_text(result["text"], encoding="utf-8")
                    console.print(f"[green]✓[/green] {audio_file.name} → {out}")
                    handle_processed_file(audio_file, action, processed_folder)
                except Exception as e:
                    err_console.print(f"✗ {audio_file.name}: {e}")

            time.sleep(interval)
    except KeyboardInterrupt:
        console.print("\nОстановлено.")
