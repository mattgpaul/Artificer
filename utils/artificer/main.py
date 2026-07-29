import argparse
from pathlib import Path
from enum import StrEnum, auto

class Language(StrEnum):
    PYTHON = auto()
    RUST = auto()

class ProjectType(StrEnum):
    LIBRARY = "lib"
    BINARY = "bin"

def setup_python_project(
        name: str, 
        project_type: ProjectType):
    # Setup python project 
    cwd = Path.cwd()
    full_path = cwd / name
    # nix
    nix_command = _nix_setup(full_path, Language.PYTHON, ProjectType.BINARY)
    print(nix_command)
    # direnv
    first, second = _direnv_setup(Language.PYTHON, full_path)
    print(first)
    print(second)
    # tracker
    print(_track_changes())
    return full_path

def _nix_setup(
        project_path: Path,
        project_language: Language,
        project_type: ProjectType,
        ):
    # execute a command string
    match project_language:
        case Language.PYTHON:
            package_manager_args = "-c uv init"
        #TODO: handle cargo command
    command = f"nix develop .#{project_language.value} {package_manager_args} {project_path}"
    return command

def _direnv_setup(project_language: Language, project_path: Path):
    envrc_command = f"echo 'use flake \"$(git rev-parse --show-toplevel)#{project_language.value}\"' > {project_path}/.envrc"
    direnv_command = f"direnv allow {project_path}"
    return (envrc_command, direnv_command)


def _track_changes():
    command = "jj st"
    return command


def main():
    path = setup_python_project(
            name="test",
            project_type=ProjectType.BINARY,
            )
    print(path)

if __name__ == "__main__":
    main()
