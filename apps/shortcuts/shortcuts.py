from pathlib import Path
# manifest of dotfiles to go through
root_dir = Path("~/Artificer/utils")
manifest = [
            "hypr/hyprland.lua",
            "nvim/lua/keymaps.lua",
            "nvim/lua/plugins/claude_inline.lua",
            "nvim/lua/plugins/lsp.lua",
            "nvim/lua/plugins/obsidian.lua",
        ]

def parse_dotfile(file: Path, identifier: str) -> dict[str, str]:
    result = {}
    with open(file, mode='r', encoding='utf-8') as f:
        str_split = f"{identifier} keybind:"
        for line in f:
            if str_split in line:
                keybind_comment = line.split(str_split)[1]
                binding = keybind_comment.split('|')[0].strip()
                description = keybind_comment.split('|')[1].strip()
                result[binding] = description
    return result

keymaps = {}
for dotfile in manifest:
    full_path = root_dir / dotfile
    expanded = full_path.expanduser()

    # All are lua files, so -- works for all of them for now
    keymaps[dotfile] = parse_dotfile(expanded, "--")

for file, binds in keymaps.items():
    print(f"\n\033[1m{file}\033[0m")
    width = max((len(k) for k in binds), default=0)
    for binding, desc in binds.items():
        print(f"    {binding:<{width}}  {desc}")
