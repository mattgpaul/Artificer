import argparse
from pathlib import Path
from enum import StrEnum, auto

class Language(StrEnum):
    PYTHON = auto()
    RUST = auto()

class ProjectType(StrEnum):
    LIBRARY = "lib"
    BINARY = "bin"

def setup_project(
        name: str, 
        project_type: ProjectType,
        language: Language,
        ):
    # Setup python project 
    cwd = Path.cwd()
    full_path = cwd / name
    # check if dir exists, and if it does, is it empty
    if full_path.exists():
        if not _is_empty(full_path):
            raise ValueError(f"{full_path} is not empty")
    # nix
    #TODO: be agnostic to project type
    _nix_setup(full_path, language, project_type)
    # direnv
    _direnv_setup(language, full_path)
    # tracker
    _track_changes()

def _is_empty(path: Path):
    return not any(path.iterdir())

def _nix_setup(
        project_path: Path,
        project_language: Language,
        project_type: ProjectType,
        ):
    # execute a command string
    match project_language:
        case Language.PYTHON:
            if project_type == ProjectType.LIBRARY:
                command_string = f"{project_language.value} -c uv init --lib {project_path}"
            else:
                command_string = f"{project_language.value} -c uv init {project_path}"
            command_string_lock = f"{project_language.value} -c uv lock"
        case Language.RUST:
            if project_type == ProjectType.LIBRARY:
                command_string = f"{project_language.value} -c cargo new --lib {project_path}"
            else:
                command_string = f"{project_language.value} -c cargo new {project_path}"
            command_string_lock = f"{project_language.value} -c cargo generate-lockfile"
    print(f"nix develop .#{command_string}")
    print(f"nix develop .#{command_string_lock}")

def _direnv_setup(project_language: Language, project_path: Path):
    print(f"echo 'use flake \"$(git rev-parse --show-toplevel)#{project_language.value}\"' > {project_path}/.envrc")
    print(f"direnv allow {project_path}")


def _track_changes():
    print("jj st")


def main():
    parser = argparse.ArgumentParser(description="Artificer CLI tool")
    
    parser.add_argument("name", help="project name")
    parser.add_argument(
            "-l", "--language",
            choices=[l.value for l in Language],
            default=Language.RUST,
            help="language (default: rust)",
            )
    parser.add_argument(
            "-t", "--type",
            choices=[t.value for t in ProjectType],
            default=ProjectType.BINARY,
            dest="project_type",
            help="project type (default: bin)"
            )

    args = parser.parse_args()

    setup_project(
            name=args.name,
            project_type=ProjectType(args.project_type),
            language=Language(args.language),
            )

if __name__ == "__main__":
    main()
