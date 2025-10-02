from __future__ import annotations
from typing import NamedTuple, Literal
from pathlib import Path
import json

import click

from .parser.record_parser import parse_log_file
from .parser.model import ModelResult
from .flight.flight import Flight
from .blender_io.exporter import (
    BlExportData,
    build_export_data as bl_build_export_data,
    bl_data_matches,
)
from .config import Config


class ClickContext(NamedTuple):
    config: Config


def parse_file(path: Path|str) -> Flight:
    parsed = parse_log_file(path)
    model = ModelResult.from_parse_result(parsed)
    flight = Flight.from_model(model)
    return flight

@click.group()
@click.option('--config', '-c',
    type=click.Path(exists=True, dir_okay=False, path_type=Path),
    default=None,
    help='Path to config file. If not given, will use the default config path.',
)
@click.pass_context
def cli(ctx: click.Context, config: Path|None):
    """Autel Logger - A tool for parsing and exporting Autel drone flight logs"""
    if config is None:
        cfg = Config.load()
    else:
        cfg = Config.load(config)
    ctx.obj = ClickContext(config=cfg)


@cli.group(name='config')
def config_group():
    """Commands for managing the application configuration"""
    pass


@config_group.command(name='show')
@click.pass_obj
def show_config(ctx: ClickContext):
    """Show the current config"""
    import pprint
    pp = pprint.PrettyPrinter(indent=2)
    d = ctx.config.serialize()
    click.echo(pp.pformat(d))



@config_group.command()
@click.option(
    '--raw-log-dir',
    type=click.Path(
        exists=True, file_okay=False, path_type=Path,
    ),
    help='Directory to store parsed raw log files (JSON format)',
)
@click.option(
    '--data-dir',
    type=click.Path(
        file_okay=False, path_type=Path,
    ),
    help='Directory to store application data files',
)
@click.option(
    '--cache-dir',
    type=click.Path(
        file_okay=False, path_type=Path,
    ),
    help='Directory to store cache files (e.g. media info)',
)
@click.option(
    '--blender-export-dir',
    type=click.Path(
        file_okay=False, path_type=Path,
    ),
    help='Directory to store Blender export files',
)
@click.pass_obj
def configure(
    ctx: ClickContext,
    raw_log_dir: Path | None,
    data_dir: Path | None,
    cache_dir: Path | None,
    blender_export_dir: Path | None,
):
    """Configure the application settings"""
    cfg = ctx.config
    changed = False
    if raw_log_dir is not None:
        raw_log_dir = raw_log_dir.expanduser().resolve()
        if not raw_log_dir.is_dir():
            raise click.ClickException(f'Raw log directory {raw_log_dir} is not a directory')
        cfg.raw_log_dir = raw_log_dir
        changed = True
    if data_dir is not None:
        data_dir = data_dir.expanduser().resolve()
        data_dir.mkdir(parents=True, exist_ok=True)
        cfg.data_dir = data_dir
        changed = True
    if cache_dir is not None:
        cache_dir = cache_dir.expanduser().resolve()
        cache_dir.mkdir(parents=True, exist_ok=True)
        cfg.cache_dir = cache_dir
        changed = True
    if blender_export_dir is not None:
        blender_export_dir = blender_export_dir.expanduser().resolve()
        blender_export_dir.mkdir(parents=True, exist_ok=True)
        cfg.blender_export_dir = blender_export_dir
        changed = True
    if not changed:
        click.echo('No changes made to config.')
        return
    cfg.save()
    click.echo(f'Config saved to {cfg.DEFAULT_FILENAME}')


@config_group.command(name='add-search-path')
@click.argument(
    'media_type',
    type=click.Choice(['video', 'image'], case_sensitive=False),
)
@click.argument(
    'search_path',
    type=click.Path(
        exists=True, file_okay=False, path_type=Path,
    ),
)
@click.option('--recursive', '-r', is_flag=True, default=False,
    help='Search recursively in subdirectories', show_default=True
)
@click.option('--glob-pattern', '-g', type=str, default=None,
    help='Glob pattern to match files (e.g. "*.mp4")',
)
@click.pass_obj
def add_media_search_path(
    ctx: ClickContext,
    media_type: Literal['video', 'image'],
    search_path: Path,
    glob_pattern: str | None,
    recursive: bool,
):
    """Add a media search path to the config file"""
    cfg = ctx.config
    search_path = search_path.expanduser().resolve()
    if not search_path.is_dir():
        raise click.ClickException(f'Path {search_path} is not a directory')
    cfg.add_media_search_path(media_type, search_path, glob_pattern, recursive)
    cfg.save()
    click.echo(f'Added {media_type} search path {search_path} to config file {cfg.DEFAULT_FILENAME}')



@cli.group(name='parse')
def parse_group():
    """Commands for parsing flight logs"""
    pass


@parse_group.command(name='list')
@click.pass_obj
def list_data_files(ctx: ClickContext):
    """List all parsed data files in the data directory"""
    cfg = ctx.config
    data_dir = cfg.raw_log_dir
    if data_dir is None:
        click.echo('Data directory is not set in config')
        return
    if not data_dir.exists():
        click.echo(f'Data directory {data_dir} does not exist')
        return
    files = [p for p in data_dir.glob('autel_*')]
    if not files:
        click.echo(f'No data files found in {data_dir}')
        return
    files.sort(key=lambda p: p.name)
    click.echo(f'Found {len(files)} data files in {data_dir}:')
    for i, f in enumerate(files):
        click.echo(f' {i+1: >2}. {f.name}')


@parse_group.command(name='file')
@click.argument('input_file', type=click.Path(
    exists=True, dir_okay=False, path_type=Path,
))
@click.option('--process-videos', is_flag=True, default=True,
    help='Search for and associate video files with the flight (if any)', show_default=True
)
@click.option('--yes', '-y', is_flag=True, default=False,
    help='Automatically confirm overwriting existing files', show_default=True
)
@click.pass_obj
def export_json(
    ctx: ClickContext,
    input_file: Path,
    process_videos: bool,
    yes: bool,
):
    """Parse flight log and export as raw JSON data"""
    # parsed = parse_log_file(input_file)
    # data = parsed.serialize()
    output_file = Flight.get_data_filename(input_file.name, ctx.config)
    click.echo(f'Exporting to {output_file}...')
    flight = parse_file(input_file)
    if process_videos:
        flight.search_videos(ctx.config)
    data = flight.serialize()
    if output_file.exists():
        try:
            existing_flight = Flight.load(output_file)
            if existing_flight == flight:
                click.echo(f'Skipping {output_file}, no changes detected.')
                return
        except Exception:
            pass
        if not yes:
            if not click.confirm(f'File {output_file} exists. Overwrite?', default=False):
                click.echo('Aborting.')
                return
    output_file.write_text(json.dumps(data, indent=2))


@parse_group.command(name='dir')
@click.argument('input_dir', type=click.Path(
    exists=True, file_okay=False, path_type=Path,
))
@click.option('--process-videos', is_flag=True, default=True,
    help='Search for and associate video files with the flight (if any)', show_default=True
)
@click.option('--yes', '-y', is_flag=True, default=False,
    help='Automatically confirm overwriting existing files', show_default=True
)
@click.pass_obj
def batch_export_json(
    ctx: ClickContext,
    input_dir: Path,
    process_videos: bool,
    yes: bool,
):
    """Parse all flight logs in a directory and export as raw JSON data"""
    input_dir = input_dir.expanduser().resolve()
    output_dir = ctx.config.data_dir

    count = 0
    skipped = 0
    click.echo(f'Processing files in {input_dir}...')
    for p in input_dir.glob('autel_*'):
        # print(p)
        if not p.is_file():
            continue
        if p.suffix != '':
            continue
        flight = parse_file(p)
        if process_videos:
            flight.search_videos(ctx.config)
        # data = flight.serialize()
        # output_file = output_dir / (p.name + '.json')
        output_file = Flight.get_data_filename(p.name, ctx.config)
        if output_file.exists():
            try:
                existing_flight = Flight.load(output_file)
                if existing_flight == flight:
                    click.echo(f'Skipping {output_file}, no changes detected.')
                    skipped += 1
                    continue
            except Exception:
                pass
            if not yes:
                if not click.confirm(f'File {output_file} exists. Overwrite?', default=False):
                    click.echo(f'Skipping {output_file}.')
                    skipped += 1
                    continue
        flight.save(output_file)
        # output_file.write_text(json.dumps(data, indent=2))
        click.echo(f'Exported {p} to {output_file}')
        count += 1
    click.echo(f'Exported {count} files ({skipped} skipped).')



@cli.group(name='blender')
def blender_group():
    """Commands for exporting to Blender"""
    pass


@blender_group.command(name='list')
@click.pass_obj
def list_blender_files(ctx: ClickContext):
    """List all Blender JSON files in the Blender export directory"""
    cfg = ctx.config
    export_dir = cfg.blender_export_dir
    if export_dir is None:
        click.echo('Blender export directory is not set in config')
        return
    if not export_dir.exists():
        click.echo(f'Blender export directory {export_dir} does not exist')
        return
    files = [p for p in export_dir.glob('*.json')]
    if not files:
        click.echo(f'No Blender JSON files found in {export_dir}')
        return
    files.sort(key=lambda p: p.name)
    click.echo(f'Found {len(files)} Blender JSON files in {export_dir}:')
    for i, f in enumerate(files):
        click.echo(f' {i+1: >2}. {f.name}')


@blender_group.command(name='file')
@click.argument('input_file', type=click.Path(
    exists=True, dir_okay=False, path_type=Path,
))
@click.option('--yes', '-y', is_flag=True, default=False,
    help='Automatically confirm overwriting existing files', show_default=True
)
@click.pass_obj
def export_blender_json(
    ctx: ClickContext,
    input_file: Path,
    yes: bool,
):
    """Parse flight log and export as Blender JSON data"""
    output_dir = ctx.config.blender_export_dir
    if output_dir is None:
        raise click.ClickException('Blender export directory is not set in config')
    if input_file.suffix == '.json':
        flight = Flight.load(input_file)
    else:
        flight = parse_file(input_file)
    output_file = output_dir / input_file.with_suffix('.json').name
    click.echo(f'Exporting to {output_file}...')
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)
    export_data = bl_build_export_data(flight)
    if output_file.exists():
        try:
            existing_data: BlExportData = json.loads(output_file.read_text())
            if bl_data_matches(existing_data, export_data):
                click.echo(f'Skipping {output_file}, no changes detected.')
                return
        except Exception:
            pass
        if not yes:
            if not click.confirm(f'File {output_file} exists. Overwrite?', default=False):
                click.echo('Aborting.')
                return
    output_file.write_text(json.dumps(export_data, indent=2))


@blender_group.command(name='dir')
@click.option('--yes', '-y', is_flag=True, default=False,
    help='Automatically confirm overwriting existing files', show_default=True
)
@click.pass_obj
def batch_export_blender_json(
    ctx: ClickContext,
    yes: bool,
):
    """Parse all flight logs in the raw logs directory and export as Blender JSON data"""
    input_dir = ctx.config.raw_log_dir
    if input_dir is None:
        raise click.ClickException('Raw log directory is not set in config')
    output_dir = ctx.config.blender_export_dir
    if output_dir is None:
        raise click.ClickException('Blender export directory is not set in config')
    if not output_dir.exists():
        output_dir.mkdir(parents=True, exist_ok=True)

    count = 0
    skipped = 0
    click.echo(f'Processing files in {input_dir}...')
    # for p in input_dir.glob('autel_*'):
    for p in input_dir.glob('*.json'):
        # print(p)
        if not p.is_file():
            continue
        # if p.suffix != '':
        #     continue
        # flight = parse_file(p)
        flight = Flight.load(p)
        export_data = bl_build_export_data(flight)
        output_file = output_dir / p.name
        if output_file.exists():
            try:
                existing_data: BlExportData = json.loads(output_file.read_text())
                if bl_data_matches(existing_data, export_data):
                    click.echo(f'Skipping {output_file}, no changes detected.')
                    skipped += 1
                    continue
                else:
                    click.echo(f'Changes detected in {output_file}, updating.')
            except Exception:
                pass
            if not yes:
                if not click.confirm(f'File {output_file} exists. Overwrite?', default=False):
                    click.echo(f'Skipping {output_file}.')
                    skipped += 1
                    continue
        output_file.write_text(json.dumps(export_data, indent=2))
        click.echo(f'Exported {p} to {output_file}')
        count += 1
    click.echo(f'Exported {count} files ({skipped} skipped).')




if __name__ == "__main__":
    cli()
