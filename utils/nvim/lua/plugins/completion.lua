return {
  {
    'saghen/blink.cmp',
    dependencies = { 'rafamadriz/friendly-snippets' },
    version = '1.*',

    ---@module 'blink.cmp'
    ---@type blink.cmp.Config
    opts = {
      keymap = {
        preset = 'super-tab',
        -- Manually summon the menu (auto_show is off). These keys are
        -- terminal-safe, unlike <C-Space> which most terminals swallow.
        ['<C-n>'] = { 'show', 'select_next', 'fallback' },
        ['<C-p>'] = { 'show', 'select_prev', 'fallback' },
      },

      appearance = {
        nerd_font_variant = 'mono',
      },

      completion = {
        -- Don't pop up suggestions automatically; summon with <C-space> or Tab.
        menu = { auto_show = false },
        documentation = { auto_show = true },
      },

      sources = {
        default = { 'lsp', 'path', 'snippets', 'buffer' },
      },

      fuzzy = { implementation = 'prefer_rust_with_warning' },
    },
  },
}
