from pathlib import Path
# manifest of dotfiles to go through
root_dir = Path("~/Artificer/utils")
manifest = [
            "hypr/hyprland.lua",
        ]

def parse_dotfile(file: Path, identifier: str) -> dict[str, str]:
    with open(expanded, mode='r', encoding='utf-8') as f:
        result = {}
        str_split = f"{identifier} keybind:"
        for line in f:
            if str_split in line:
                keybind_comment = line.split(str_split)[1]
                binding = keybind_comment.split('|')[0].strip()
                description = keybind_comment.split('|')[1].strip()
                result[binding] = description
        return result

for dotfile in manifest:
    full_path = root_dir / dotfile
    expanded = full_path.expanduser()

    hyprfile = parse_dotfile(expanded, "--")
    print(hyprfile)

