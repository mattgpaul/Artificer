set background=dark
hi clear
if exists("syntax_on")
  syntax reset
endif
let g:colors_name = "matts-green"

" ── Core UI ──────────────────────────────────────────────────────────────────
hi Normal       guifg=#04ff00 guibg=#000000
hi NonText      guifg=#555753 guibg=#000000
hi LineNr       guifg=#555753 guibg=#000000
hi CursorLineNr guifg=#04ff00 guibg=#0a0a0a gui=none
hi CursorLine   guibg=#0a0a0a gui=none
hi CursorColumn guibg=#0a0a0a
hi ColorColumn  guibg=#0a0a0a
hi SignColumn   guifg=#555753 guibg=#000000
hi VertSplit    guifg=#1a1a1a guibg=#000000
hi StatusLine   guifg=#04ff00 guibg=#000000 gui=none
hi StatusLineNC guifg=#555753 guibg=#0a0a0a gui=none
hi TabLine      guifg=#555753 guibg=#0a0a0a gui=underline
hi TabLineSel   guifg=#04ff00 guibg=#000000 gui=none
hi TabLineFill  guibg=#000000
hi Visual       guibg=#002800
hi Search       guifg=#000000 guibg=#04ff00
hi IncSearch    guifg=#000000 guibg=#8ae234
hi MatchParen   guifg=#04ff00 guibg=#002200 gui=bold
hi Folded       guifg=#555753 guibg=#0a0a0a
hi FoldColumn   guifg=#555753 guibg=#000000
hi Pmenu        guifg=#04ff00 guibg=#0a0a0a
hi PmenuSel     guifg=#000000 guibg=#04ff00
hi PmenuSbar    guibg=#1a1a1a
hi PmenuThumb   guibg=#04ff00
hi WildMenu     guifg=#000000 guibg=#04ff00
hi Directory    guifg=#eeeeec
hi Title        guifg=#04ff00 gui=bold
hi Question     guifg=#04ff00 gui=bold
hi MoreMsg      guifg=#04ff00 gui=bold
hi WarningMsg   guifg=#ef2929
hi ErrorMsg     guifg=#ef2929 guibg=#000000
hi Error        guifg=#ef2929 guibg=#1a0000
hi SpellBad     guisp=#ef2929 gui=undercurl
hi SpellWarn    guisp=#c4a000 gui=undercurl
hi Conceal      guifg=#555753 guibg=#000000

" ── Syntax ───────────────────────────────────────────────────────────────────
hi Comment      guifg=#555753 gui=italic
hi Constant     guifg=#34e2e2
hi String       guifg=#c07830
hi Character    guifg=#c07830
hi Number       guifg=#34e2e2
hi Boolean      guifg=#34e2e2
hi Float        guifg=#34e2e2
hi Identifier   guifg=#04ff00 gui=none
hi Function     guifg=#04ff00
hi Statement    guifg=#eeeeec gui=bold
hi Conditional  guifg=#eeeeec gui=bold
hi Repeat       guifg=#eeeeec gui=bold
hi Label        guifg=#729fcf
hi Operator     guifg=#eeeeec gui=bold
hi Keyword      guifg=#eeeeec gui=bold
hi Exception    guifg=#eeeeec gui=bold
hi PreProc      guifg=#729fcf
hi Include      guifg=#729fcf
hi Define       guifg=#729fcf
hi Macro        guifg=#729fcf
hi PreCondit    guifg=#729fcf
hi Type         guifg=#34e2e2
hi StorageClass guifg=#eeeeec gui=bold
hi Structure    guifg=#34e2e2
hi Typedef      guifg=#34e2e2
hi Special      guifg=#ef2929
hi SpecialChar  guifg=#ef2929
hi Tag          guifg=#729fcf
hi Delimiter    guifg=#8ae234
hi SpecialComment guifg=#555753 gui=italic
hi Debug        guifg=#ef2929
hi Underlined   guifg=#729fcf gui=underline
hi Ignore       guifg=#555753
hi Todo         guifg=#000000 guibg=#c4a000 gui=bold

" ── Diff ─────────────────────────────────────────────────────────────────────
hi DiffAdd      guifg=#04ff00 guibg=#001400
hi DiffChange   guifg=#c4a000 guibg=#1a1400
hi DiffDelete   guifg=#cc0000 guibg=#1a0000
hi DiffText     guifg=#c4a000 guibg=#332800 gui=bold
