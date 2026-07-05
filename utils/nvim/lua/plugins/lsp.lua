vim.lsp.config('pyright', {
  cmd = { 'pyright-langserver', '--stdio' },
  filetypes = { 'python' },
  root_markers = { 'pyproject.toml', 'setup.py', 'setup.cfg', 'requirements.txt', '.git' },
  root_dir = function(bufnr, on_dir)
    local fname = vim.api.nvim_buf_get_name(bufnr)
    local root = vim.fs.root(fname, { 'pyproject.toml', 'setup.py', 'setup.cfg', 'requirements.txt', '.git' })
    on_dir(root or vim.fn.getcwd())
  end,
  settings = {
    python = {
      pythonPath = vim.fn.exepath('python3') or vim.fn.exepath('python') or 'python',
    },
  },
})

vim.lsp.config('rust_analyzer', {
  cmd = { 'rust-analyzer' },
  filetypes = { 'rust' },
  root_markers = { 'Cargo.toml', 'rust-project.json' },
})

vim.lsp.enable({ 'pyright', 'rust_analyzer' })

-- No inline diagnostics; view them on demand with <leader>e (open_float).
vim.diagnostic.config({
  underline = false,
  virtual_text = false,
  severity_sort = true,
})

vim.api.nvim_create_autocmd('LspAttach', {
  callback = function(args)
    local opts = { buffer = args.buf }
    vim.keymap.set('n', 'gd', vim.lsp.buf.definition, opts) -- keybind: gd|LSP go to definition
    vim.keymap.set('n', 'gD', vim.lsp.buf.declaration, opts) -- keybind: gD|LSP go to declaration
    vim.keymap.set('n', 'gi', vim.lsp.buf.implementation, opts) -- keybind: gi|LSP go to implementation
    vim.keymap.set('n', 'gr', vim.lsp.buf.references, opts) -- keybind: gr|LSP list references
    vim.keymap.set('n', 'gy', vim.lsp.buf.type_definition, opts) -- keybind: gy|LSP go to type definition
    vim.keymap.set('n', 'K', vim.lsp.buf.hover, opts) -- keybind: K|LSP hover docs
    vim.keymap.set('n', '<C-k>', vim.lsp.buf.signature_help, opts) -- keybind: <C-k>|LSP signature help
    vim.keymap.set('n', '<leader>rn', vim.lsp.buf.rename, opts) -- keybind: <leader>rn|LSP rename symbol
    vim.keymap.set({ 'n', 'v' }, '<leader>ca', vim.lsp.buf.code_action, opts) -- keybind: <leader>ca|LSP code action
    vim.keymap.set('n', '<leader>f', function() vim.lsp.buf.format({ async = true }) end, opts) -- keybind: <leader>f|LSP format buffer (async)
    vim.keymap.set('n', '[d', vim.diagnostic.goto_prev, opts) -- keybind: [d|Go to previous diagnostic
    vim.keymap.set('n', ']d', vim.diagnostic.goto_next, opts) -- keybind: ]d|Go to next diagnostic
    vim.keymap.set('n', '<leader>e', vim.diagnostic.open_float, opts) -- keybind: <leader>e|Open diagnostic float
  end,
})

return {
  {
    "mason-org/mason.nvim",
    opts = {
      ui = {
        icons = {
          package_installed = "✓",
          package_pending = "➜",
          package_uninstalled = "✗",
        },
      },
    },
  },
}
