import logging
import logging.handlers
import os
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from tool_audio import config as cfg
from tool_audio import storage
from tool_audio.polisher import ERROR_PREFIX, polish_text
from tool_audio.transcriber import transcribe
from tool_audio.utils import collect_audio_files, handle_processed_file, output_path

app = typer.Typer(
    name="transcribe",
    help="Локальная транскрибация аудио/видео-файлов в текст (Whisper, CPU).",
    add_completion=False,
)
config_app = typer.Typer(
    name="transcribe-config",
    help="Управление конфигурацией tool-audio.",
    add_completion=False,
)

console = Console()
err_console = Console(stderr=True, style="bold red")


def _setup_logger() -> logging.Logger:
    log_path = cfg.get_log_path()
    max_bytes = cfg.get_log_max_bytes()
    log_path.parent.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("tool_audio")
    if logger.handlers:
        return logger
    handler = logging.handlers.RotatingFileHandler(
        log_path, maxBytes=max_bytes, backupCount=3, encoding="utf-8"
    )
    handler.setFormatter(logging.Formatter("%(asctime)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)
    return logger


def _fmt_duration(seconds: float) -> str:
    s = int(seconds)
    return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"


def _ts() -> str:
    return datetime.now().strftime("%H:%M:%S")


def _fmt_elapsed(start: datetime) -> str:
    s = int((datetime.now() - start).total_seconds())
    if s < 60:
        return f"{s}s"
    return f"{s // 60}m {s % 60:02d}s"


def _print(icon: str, icon_style: str, name: str, model: str, elapsed: str = "", extra: str = "", path: Path | None = None) -> None:
    parts = [
        f"[dim]{_ts()}[/dim]",
        f"[{icon_style}]{icon}[/{icon_style}]",
        name,
        f"[dim][{model}][/dim]",
    ]
    if elapsed:
        parts.append(f"[dim]{elapsed}[/dim]")
    if extra:
        parts.append(f"[dim]{extra}[/dim]")
    if path is not None:
        parts.append(f"[dim]→  {path}[/dim]")
    console.print("  ".join(parts))


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


@config_app.command("set-output")
def config_set_output(
    path: Path = typer.Argument(..., help="Папка для сохранения сырого текста транскрибации."),
) -> None:
    """Установить папку для сырого вывода транскрибации."""
    data = cfg.load()
    data["default_output"] = str(path.expanduser().resolve())
    cfg.save(data)
    console.print(f"[green]✓[/green] Папка вывода установлена: [cyan]{path.expanduser().resolve()}[/cyan]")


@config_app.command("set-polish-output")
def config_set_polish_output(
    path: Path = typer.Argument(..., help="Папка для сохранения очищенного текста (DeepSeek)."),
) -> None:
    """Установить папку для очищенного вывода (DeepSeek)."""
    data = cfg.load()
    data["polish_output"] = str(path.expanduser().resolve())
    cfg.save(data)
    console.print(f"[green]✓[/green] Папка очищенного вывода установлена: [cyan]{path.expanduser().resolve()}[/cyan]")


@config_app.command("set-raw-done")
def config_set_raw_done(
    path: Path = typer.Argument(..., help="Папка для сырого текста после успешной полировки."),
) -> None:
    """Установить папку для сырого текста после полировки (raw Done)."""
    data = cfg.load()
    data["raw_done_folder"] = str(path.expanduser().resolve())
    cfg.save(data)
    console.print(f"[green]✓[/green] Папка raw Done установлена: [cyan]{path.expanduser().resolve()}[/cyan]")


@config_app.command("show")
def config_show() -> None:
    """Показать текущую конфигурацию."""
    data = cfg.load()
    console.print(f"[bold]Конфиг:[/bold] {cfg.CONFIG_PATH}")
    for key, value in data.items():
        console.print(f"  {key} = {value}")
    defaults = {
        "default_source": cfg.get_default_source(),
        "default_output": cfg.get_default_output(),
        "polish_output": cfg.get_polish_output(),
        "deepseek_model": cfg.get_deepseek_model(),
        "default_model": cfg.get_default_model() or "base",
    }
    console.print("\n[bold]Эффективные значения:[/bold]")
    for key, value in defaults.items():
        marker = "" if key in data else " [dim](по умолчанию)[/dim]"
        console.print(f"  {key} = {value}{marker}")


def _do_polish(text: str, raw_name: str, polish_out: Path) -> bool:
    """Очищает текст через настроенного провайдера, сохраняет и печатает статус. Возвращает True при успехе."""
    provider = cfg.get_polish_provider()
    model = cfg.get_groq_model() if provider == "groq" else cfg.get_deepseek_model()
    p_start = datetime.now()
    _print("◦", "dim", raw_name, model, extra="очистка")
    polished = polish_text(text, model=model, provider=provider)
    polish_out.parent.mkdir(parents=True, exist_ok=True)
    polish_out.write_text(polished, encoding="utf-8")
    if polished.startswith(ERROR_PREFIX):
        _print("⚠", "yellow", raw_name, model, elapsed=_fmt_elapsed(p_start), path=polish_out)
        return False
    _print("✦", "cyan", raw_name, model, elapsed=_fmt_elapsed(p_start), path=polish_out)
    return True


@app.command()
def polish(
    source: Optional[Path] = typer.Argument(
        None,
        help="Текстовый файл или папка для очистки. Если не указан — берётся default_output из конфига.",
    ),
    output: Optional[Path] = typer.Option(
        None,
        "--output", "-o",
        help="Куда сохранить результат. По умолчанию — папка polish_output из конфига.",
    ),
) -> None:
    """Очищает текстовый файл(ы) через DeepSeek."""
    if source is None:
        source = cfg.get_default_output()
        if source is None:
            err_console.print(
                "Ошибка: не указан source и не задана default_output. "
                "Используй: transcribe-config set-output /path/to/folder"
            )
            raise typer.Exit(1)
        console.print(f"[dim]Источник из конфига: {source}[/dim]")

    if not source.exists():
        err_console.print(f"Ошибка: путь не найден: '{source}'")
        raise typer.Exit(1)

    files = [source] if source.is_file() else sorted(source.glob("*.md"))
    if not files:
        err_console.print(f"Нет .md файлов в папке: '{source}'")
        raise typer.Exit(1)

    polish_dir = cfg.get_polish_output()
    raw_done_folder = cfg.get_raw_done_folder()
    success, failed = 0, 0

    for file in files:
        raw_text = file.read_text(encoding="utf-8")
        if output and source.is_file():
            out = output
        elif output:
            out = output / file.name
        else:
            out = polish_dir / file.name

        ok = _do_polish(raw_text, file.name, out)
        if ok:
            handle_processed_file(file, "move", raw_done_folder)
            success += 1
        else:
            failed += 1

    if len(files) > 1:
        console.print(f"\nГотово: [cyan]{success}[/cyan] очищено, [red]{failed}[/red] с ошибками.")
    if failed:
        raise typer.Exit(1)


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
    whisper_model = f"whisper-{model}"

    logger = _setup_logger()
    pid = os.getpid()
    logger.info(f"TRANSCRIBE_START pid={pid} source={source}")

    console.print(f"[bold]Файлов:[/bold] {len(files)}  [bold]Модель:[/bold] {whisper_model}  [bold]Язык:[/bold] {language}\n")

    success, failed = 0, 0

    for audio_file in files:
        out = output_path(audio_file, output_dir)
        t_start = datetime.now()
        _print("▶", "dim", audio_file.name, whisper_model, extra="транскрибация")
        logger.info(f"FILE_START pid={pid} file={audio_file.name}")

        try:
            with Progress(SpinnerColumn(), TextColumn("  [dim]{task.description}[/dim]"), transient=True, console=console) as progress:
                progress.add_task("обработка…")
                text, audio_dur = transcribe(audio_file, model_name=model, language=language)

            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_text(text, encoding="utf-8")
            _print("✓", "green", audio_file.name, whisper_model,
                   elapsed=_fmt_elapsed(t_start), extra=f"audio {_fmt_duration(audio_dur)}", path=out)
            logger.info(f"FILE_DONE pid={pid} file={audio_file.name} audio={_fmt_duration(audio_dur)} output={out}")

            polish_ok = _do_polish(text, out.name, cfg.get_polish_output() / out.name)
            if polish_ok:
                handle_processed_file(out, "move", cfg.get_raw_done_folder())

            handle_processed_file(audio_file, action, processed_folder)
            success += 1
        except Exception as e:
            _print("✗", "red", audio_file.name, whisper_model, elapsed=_fmt_elapsed(t_start), extra=str(e))
            logger.info(f"FILE_ERROR pid={pid} file={audio_file.name} error={e}")
            failed += 1

    logger.info(f"TRANSCRIBE_DONE pid={pid} success={success} failed={failed}")
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
    whisper_model = f"whisper-{model}"

    logger = _setup_logger()
    pid = os.getpid()

    lock_path = cfg.CONFIG_PATH.parent / "watch.lock"
    if lock_path.exists():
        old_pid = lock_path.read_text().strip()
        if old_pid and Path(f"/proc/{old_pid}").exists():
            err_console.print(f"Ошибка: watch уже запущен (pid={old_pid}). Останови его или сервис: systemctl --user stop tool-audio")
            raise typer.Exit(1)
    lock_path.write_text(str(pid))

    polish_out = cfg.get_polish_output()
    raw_done = cfg.get_raw_done_folder()
    logger.info(
        f"WATCH_START pid={pid}"
        f" source={source}"
        f" output={output_dir}"
        f" polish_out={polish_out}"
        f" raw_done={raw_done}"
        f" model={whisper_model}"
        f" interval={interval}s"
    )

    storage.init_db()

    console.print(f"Мониторинг: [cyan]{source}[/cyan]  [dim]модель: {whisper_model}  интервал: {interval}s[/dim]")
    console.print("[dim]Ctrl+C для остановки[/dim]\n")

    try:
        while True:
            try:
                files = collect_audio_files(source)
            except (ValueError, FileNotFoundError):
                files = []

            new_files = [(f, h) for f in files if not storage.is_processed(h := storage.file_hash(f))]
            for audio_file, h in new_files:
                storage.add_job(audio_file, h)
                out = output_path(audio_file, output_dir)
                t_start = datetime.now()
                _print("▶", "dim", audio_file.name, whisper_model, extra="транскрибация")
                logger.info(f"FILE_START pid={pid} file={audio_file.name}")

                try:
                    result: dict = {}

                    def _run(af=audio_file, m=model, lang=language, r=result):
                        try:
                            r["text"], r["duration"] = transcribe(af, model_name=m, language=lang)
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
                    audio_dur = _fmt_duration(result["duration"])
                    _print("✓", "green", audio_file.name, whisper_model,
                           elapsed=_fmt_elapsed(t_start), extra=f"audio {audio_dur}", path=out)
                    logger.info(
                        f"FILE_DONE pid={pid} file={audio_file.name}"
                        f" audio={audio_dur} elapsed={_fmt_elapsed(t_start)} output={out}"
                    )

                    storage.mark_done(h)
                    polish_ok = _do_polish(result["text"], out.name, cfg.get_polish_output() / out.name)
                    if polish_ok:
                        handle_processed_file(out, "move", cfg.get_raw_done_folder())
                    handle_processed_file(audio_file, action, processed_folder)
                except Exception as e:
                    storage.mark_error(h, str(e))
                    _print("✗", "red", audio_file.name, whisper_model, elapsed=_fmt_elapsed(t_start), extra=str(e))
                    logger.info(f"FILE_ERROR pid={pid} file={audio_file.name} error={e}")

            time.sleep(interval)
    except KeyboardInterrupt:
        logger.info(f"WATCH_STOP pid={pid}")
        console.print("\nОстановлено.")
    finally:
        lock_path.unlink(missing_ok=True)
