vim.o.termguicolors = false
vim.cmd.colorscheme("vim")

-- Neovim's "vim" colorscheme uses hardcoded 256-color values for some groups
-- instead of the basic 16 ANSI colors that Vim's default uses. Override them
-- so colors come from the terminal palette, matching Vim's actual behavior.

local overrides = {
  -- Syntax groups
  PreProc    = { ctermfg = 12 },              -- was 81
  Type       = { ctermfg = 10 },              -- was 121
  Special    = { ctermfg = 9 },               -- was 224
  Underlined = { ctermfg = 12, underline = true }, -- was 81

  -- UI groups
  SpecialKey       = { ctermfg = 14 },                        -- was 81
  Directory        = { ctermfg = 14 },                        -- was 159
  MoreMsg          = { ctermfg = 10, bold = true },           -- was 121
  Question         = { ctermfg = 10, bold = true },           -- was 121
  Title            = { ctermfg = 13, bold = true },           -- was 225
  WarningMsg       = { ctermfg = 9 },                         -- was 224
  Visual           = { cterm = { reverse = true } },          -- was fg=0 bg=248
  Folded           = { ctermfg = 14, ctermbg = 8 },           -- bg was 242
  FoldColumn       = { ctermfg = 14, ctermbg = 8 },           -- bg was 242
  SignColumn       = { ctermfg = 14, ctermbg = 8 },           -- bg was 242
  CursorColumn     = { ctermbg = 8 },                         -- was 242
  Pmenu            = { ctermfg = 15, ctermbg = 0 },           -- popup menu background
  PmenuSel         = { ctermbg = 8 },                         -- was fg=242 bg=0
  PmenuSbar        = { ctermbg = 7 },                         -- was 248
  PmenuThumb       = { ctermbg = 15 },                        -- scrollbar thumb
  TabLine          = { ctermfg = 15, ctermbg = 8, underline = true }, -- bg was 242
  NormalFloat      = { ctermfg = 15, ctermbg = 0 },           -- floating windows
  FloatBorder      = { ctermfg = 8, ctermbg = 0 },            -- floating window borders
  StatusLineTerm   = { ctermfg = 15, ctermbg = 2, bold = true },      -- was fg=0 bg=121
  StatusLineTermNC = { ctermfg = 15, ctermbg = 2 },                   -- was fg=0 bg=121
}

for group, attrs in pairs(overrides) do
  vim.api.nvim_set_hl(0, group, attrs)
end
