from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from audio_transcriber.transcriber import transcribe
from audio_transcriber.utils import collect_audio_files, output_path

app = typer.Typer(
    name="transcribe",
    help="Локальная транскрибация аудио/видео-файлов в текст (Whisper, CPU).",
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True, style="bold red")


@app.command()
def main(
    source: Path = typer.Argument(
        ...,
        help="Путь к аудио-файлу или директории с аудио-файлами.",
        exists=True,
        readable=True,
    ),
    output_dir: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Директория для сохранения TXT-файлов (по умолчанию — рядом с исходным файлом).",
    ),
    model: str = typer.Option(
        "base",
        "--model", "-m",
        help="Размер модели Whisper: tiny, base, small, medium, large.",
    ),
    language: str = typer.Option(
        "ru",
        "--lang", "-l",
        help="Код языка транскрибации (ru, en, ...).",
    ),
) -> None:
    """Транскрибирует аудио/видео-файл(ы) в TXT."""
    if output_dir:
        output_dir.mkdir(parents=True, exist_ok=True)

    try:
        files = collect_audio_files(source)
    except (ValueError, FileNotFoundError) as e:
        err_console.print(f"Ошибка: {e}")
        raise typer.Exit(1)

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
                out.write_text(text, encoding="utf-8")
                console.print(f"[green]✓[/green] {audio_file.name} → [dim]{out}[/dim]")
                success += 1
            except Exception as e:
                err_console.print(f"✗ {audio_file.name}: {e}")
                failed += 1

    console.print(f"\nГотово: [green]{success}[/green] успешно, [red]{failed}[/red] с ошибками.")
    if failed:
        raise typer.Exit(1)
