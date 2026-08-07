"""
Nightcore Maker
---------------
Lee mp3 de la carpeta nightcoreBase/, aplica un cambio de velocidad+pitch
(el mismo efecto "vinculado" que usa el nightcore clásico) y guarda el
resultado en nightcore/.

Uso: python3 nightcore_maker.py
"""

import sys
from pathlib import Path

from pydub import AudioSegment
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, FloatPrompt
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    TextColumn,
    BarColumn,
    TaskProgressColumn,
    TimeElapsedColumn,
)
from rich import box

console = Console()

BASE_DIR = Path("nightcoreBase")
OUTPUT_DIR = Path("nightcore")
BATCH_DIR = OUTPUT_DIR / "al_por_mayor"


def setup_dirs() -> None:
    BASE_DIR.mkdir(exist_ok=True)
    OUTPUT_DIR.mkdir(exist_ok=True)
    BATCH_DIR.mkdir(exist_ok=True)


def list_mp3_files() -> list[Path]:
    return sorted(BASE_DIR.glob("*.mp3"))


def show_banner() -> None:
    console.print(
        Panel.fit(
            "[bold magenta]NIGHTCORE MAKER[/bold magenta]\n"
            "[dim]Convertí tus canciones a nightcore / slowed[/dim]",
            border_style="magenta",
        )
    )


def show_file_table(files: list[Path]) -> None:
    table = Table(title="Canciones disponibles", box=box.ROUNDED, header_style="bold cyan")
    table.add_column("#", justify="right", style="bold yellow")
    table.add_column("Archivo", style="white")
    for i, f in enumerate(files, start=1):
        table.add_row(str(i), f.name)
    console.print(table)


def choose_file(files: list[Path]) -> Path:
    while True:
        choice = Prompt.ask("[bold cyan]Elegí el número de la canción[/bold cyan]")
        if choice.isdigit() and 1 <= int(choice) <= len(files):
            return files[int(choice) - 1]
        console.print("[red]Opción inválida, probá de nuevo.[/red]")


def ask_factor() -> float:
    while True:
        factor = FloatPrompt.ask(
            "[bold cyan]Factor de velocidad/pitch[/bold cyan] "
            "(ej: [green]1.5[/green] = nightcore, [blue]0.8[/blue] = slowed)"
        )
        if factor <= 0:
            console.print("[red]Tiene que ser mayor que 0.[/red]")
            continue
        return factor


def make_nightcore(input_path: Path, factor: float, dest_dir: Path = OUTPUT_DIR) -> Path:
    """
    Cambia velocidad y pitch juntos (efecto nightcore/slowed clásico):
    se reinterpreta el sample rate del audio y luego se vuelve a
    samplear al original, lo que hace que se reproduzca más rápido/lento
    y, de yapa, más agudo/grave -- exactamente como el nightcore real.
    """
    audio = AudioSegment.from_mp3(input_path)
    original_rate = audio.frame_rate
    new_frame_rate = int(original_rate * factor)

    shifted = audio._spawn(audio.raw_data, overrides={"frame_rate": new_frame_rate})
    shifted = shifted.set_frame_rate(original_rate)

    suffix = "nightcore" if factor >= 1 else "slowed"
    out_name = f"{input_path.stem}_{suffix}_{factor}.mp3"
    out_path = dest_dir / out_name
    shifted.export(out_path, format="mp3")
    return out_path


def batch_convert(files: list[Path], factor: float) -> list[Path]:
    """Convierte todas las canciones de la lista con el mismo factor,
    mostrando progreso (archivo actual, cuántos van, tiempo transcurrido)."""
    results: list[Path] = []

    progress = Progress(
        SpinnerColumn(),
        TextColumn("[bold cyan]{task.fields[current_file]}"),
        BarColumn(),
        TaskProgressColumn(),
        TextColumn("• {task.completed}/{task.total} canciones"),
        TimeElapsedColumn(),
        console=console,
    )

    with progress:
        task = progress.add_task(
            "convirtiendo", total=len(files), current_file=files[0].name
        )
        for f in files:
            progress.update(task, current_file=f.name)
            out_path = make_nightcore(f, factor, dest_dir=BATCH_DIR)
            results.append(out_path)
            progress.advance(task)

    return results


def show_menu() -> str:
    console.print()
    table = Table(box=box.SIMPLE, show_header=False)
    table.add_row("[bold yellow]1[/bold yellow]", "Convertir una canción")
    table.add_row("[bold yellow]2[/bold yellow]", "Convertir TODAS (al por mayor)")
    table.add_row("[bold yellow]3[/bold yellow]", "Salir")
    console.print(table)
    return Prompt.ask(
        "[bold cyan]Elegí una opción[/bold cyan]", choices=["1", "2", "3"], default="1"
    )


def run_single(files: list[Path]) -> None:
    show_file_table(files)
    chosen = choose_file(files)
    factor = ask_factor()

    with console.status("[bold green]Procesando audio...[/bold green]"):
        out_path = make_nightcore(chosen, factor)

    console.print(
        Panel.fit(
            f"[bold green]Listo![/bold green]\nGuardado en: [cyan]{out_path}[/cyan]",
            border_style="green",
        )
    )


def run_batch(files: list[Path]) -> None:
    console.print(f"[dim]Se van a convertir {len(files)} canciones con el mismo factor.[/dim]")
    factor = ask_factor()

    results = batch_convert(files, factor)

    console.print(
        Panel.fit(
            f"[bold green]Listo! Se convirtieron {len(results)} canciones.[/bold green]\n"
            f"Guardadas en: [cyan]{BATCH_DIR}/[/cyan]",
            border_style="green",
        )
    )


def main() -> None:
    setup_dirs()
    show_banner()

    while True:
        files = list_mp3_files()
        if not files:
            console.print(f"[red]No hay archivos .mp3 en la carpeta '{BASE_DIR}/'.[/red]")
            console.print(f"[yellow]Poné algunos mp3 ahí y volvé a correr el script.[/yellow]")
            sys.exit(1)

        option = show_menu()

        if option == "1":
            run_single(files)
        elif option == "2":
            run_batch(files)
        else:
            console.print("[dim]Listo, nos vemos![/dim]")
            break

        again = Prompt.ask(
            "[bold cyan]¿Volver al menú? (s/n)[/bold cyan]", choices=["s", "n"], default="s"
        )
        if again == "n":
            console.print("[dim]Listo, nos vemos![/dim]")
            break


if __name__ == "__main__":
    main()