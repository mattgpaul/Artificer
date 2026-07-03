set background=dark
hi clear
if exists("syntax_on")
  syntax reset
endif
let g:colors_name = "dead-world"

" Sun Eater "dead world" — ember on deep teal
" bg #0e1614  bg2 #18231f  line #141f1b  fg #d8d2c8  mint #9fb2aa
" ember #e0631f  crimson #b23a1e  teal #3c6b5e  bright-teal #5e9f8e
" amber #d4913c  bright-amber #f0b45c  moss #5e8f6e  slate #7a9ab0

" ── Core UI ──────────────────────────────────────────────────────────────────
hi Normal       guifg=#d8d2c8 guibg=#0e1614
hi NonText      guifg=#3c4a44 guibg=#0e1614
hi LineNr       guifg=#3c4a44 guibg=#0e1614
hi CursorLineNr guifg=#e0631f guibg=#141f1b gui=none
hi CursorLine   guibg=#141f1b gui=none
hi CursorColumn guibg=#141f1b
hi ColorColumn  guibg=#141f1b
hi SignColumn   guifg=#3c4a44 guibg=#0e1614
hi VertSplit    guifg=#18231f guibg=#0e1614
hi StatusLine   guifg=#d8d2c8 guibg=#18231f gui=none
hi StatusLineNC guifg=#9fb2aa guibg=#141f1b gui=none
hi TabLine      guifg=#9fb2aa guibg=#141f1b gui=underline
hi TabLineSel   guifg=#e0631f guibg=#0e1614 gui=none
hi TabLineFill  guibg=#0e1614
hi Visual       guibg=#2a3d38
hi Search       guifg=#0e1614 guibg=#e0631f
hi IncSearch    guifg=#0e1614 guibg=#f0b45c
hi MatchParen   guifg=#e0631f guibg=#2a3d38 gui=bold
hi Folded       guifg=#9fb2aa guibg=#18231f
hi FoldColumn   guifg=#3c4a44 guibg=#0e1614
hi Pmenu        guifg=#d8d2c8 guibg=#18231f
hi PmenuSel     guifg=#0e1614 guibg=#e0631f
hi PmenuSbar    guibg=#2a3d38
hi PmenuThumb   guibg=#e0631f
hi WildMenu     guifg=#0e1614 guibg=#e0631f
hi Directory    guifg=#5e9f8e
hi Title        guifg=#e0631f gui=bold
hi Question     guifg=#5e9f8e gui=bold
hi MoreMsg      guifg=#5e8f6e gui=bold
hi WarningMsg   guifg=#f0b45c
hi ErrorMsg     guifg=#b23a1e guibg=#0e1614
hi Error        guifg=#e0631f guibg=#1a0a06
hi SpellBad     guisp=#b23a1e gui=undercurl
hi SpellWarn    guisp=#d4913c gui=undercurl
hi Conceal      guifg=#3c4a44 guibg=#0e1614

" ── Syntax ───────────────────────────────────────────────────────────────────
hi Comment      guifg=#5a6b64 gui=italic
hi Constant     guifg=#5e9f8e
hi String       guifg=#d4913c
hi Character    guifg=#d4913c
hi Number       guifg=#5e9f8e
hi Boolean      guifg=#5e9f8e
hi Float        guifg=#5e9f8e
hi Identifier   guifg=#d8d2c8 gui=none
hi Function     guifg=#f0b45c
hi Statement    guifg=#e0631f gui=bold
hi Conditional  guifg=#e0631f gui=bold
hi Repeat       guifg=#e0631f gui=bold
hi Label        guifg=#7a9ab0
hi Operator     guifg=#9fb2aa
hi Keyword      guifg=#e0631f gui=bold
hi Exception    guifg=#e0631f gui=bold
hi PreProc      guifg=#7a9ab0
hi Include      guifg=#7a9ab0
hi Define       guifg=#7a9ab0
hi Macro        guifg=#7a9ab0
hi PreCondit    guifg=#7a9ab0
hi Type         guifg=#7a9ab0
hi StorageClass guifg=#e0631f gui=bold
hi Structure    guifg=#7a9ab0
hi Typedef      guifg=#7a9ab0
hi Special      guifg=#e0631f
hi SpecialChar  guifg=#e0631f
hi Tag          guifg=#7a9ab0
hi Delimiter    guifg=#9fb2aa
hi SpecialComment guifg=#5a6b64 gui=italic
hi Debug        guifg=#b23a1e
hi Underlined   guifg=#5e9f8e gui=underline
hi Ignore       guifg=#3c4a44
hi Todo         guifg=#0e1614 guibg=#d4913c gui=bold

" ── Diagnostics (LSP) ────────────────────────────────────────────────────────
hi DiagnosticError guifg=#e0631f
hi DiagnosticWarn  guifg=#d4913c
hi DiagnosticInfo  guifg=#5e9f8e
hi DiagnosticHint  guifg=#9fb2aa
hi DiagnosticUnderlineError guisp=#e0631f gui=undercurl
hi DiagnosticUnderlineWarn  guisp=#d4913c gui=undercurl
hi DiagnosticUnderlineInfo  guisp=#5e9f8e gui=undercurl
hi DiagnosticUnderlineHint  guisp=#9fb2aa gui=undercurl

" ── Diff ─────────────────────────────────────────────────────────────────────
hi DiffAdd      guifg=#5e8f6e guibg=#10201a
hi DiffChange   guifg=#d4913c guibg=#1f1810
hi DiffDelete   guifg=#b23a1e guibg=#1f0f0a
hi DiffText     guifg=#d4913c guibg=#33280f gui=bold

" ── Treesitter captures (neovim) ─────────────────────────────────────────────
hi link @comment          Comment
hi link @comment.todo     Todo
hi link @comment.note     SpecialComment
hi link @comment.warning  WarningMsg
hi link @comment.error    Error

hi @variable              guifg=#d8d2c8
hi @variable.builtin      guifg=#e0631f
hi @variable.parameter    guifg=#9fb2aa
hi @variable.member       guifg=#7a9ab0

hi link @constant         Constant
hi @constant.builtin      guifg=#5e9f8e
hi link @constant.macro   Define
hi @module                guifg=#7a9ab0
hi @namespace             guifg=#7a9ab0
hi link @label            Label

hi link @string           String
hi @string.escape         guifg=#e0631f
hi link @string.special   Special
hi link @character        Character
hi link @number           Number
hi link @boolean          Boolean
hi link @float            Float

hi link @function         Function
hi @function.builtin      guifg=#f0b45c
hi link @function.call    Function
hi link @function.method  Function
hi link @constructor      Structure

hi link @keyword             Keyword
hi @keyword.function         guifg=#e0631f gui=bold
hi @keyword.operator         guifg=#e0631f gui=bold
hi @keyword.return           guifg=#e0631f gui=bold
hi link @keyword.conditional Conditional
hi link @keyword.repeat      Repeat
hi link @keyword.import      Include
hi link @keyword.exception   Exception

hi link @operator         Operator
hi link @type             Type
hi @type.builtin          guifg=#5e9f8e
hi link @type.definition  Typedef
hi @attribute             guifg=#7a9ab0
hi @property              guifg=#7a9ab0
hi @field                 guifg=#7a9ab0

hi @punctuation.delimiter guifg=#9fb2aa
hi @punctuation.bracket   guifg=#9fb2aa
hi @punctuation.special   guifg=#e0631f

hi link @tag              Tag
hi @tag.attribute         guifg=#7a9ab0
hi @tag.delimiter         guifg=#9fb2aa
