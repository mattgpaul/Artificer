vim.lsp.config("lua_ls", {
	cmd = { 'lua-language-server' },
	filetypes = { 'lua' },
	root_markers = { '.luarc.json', '.luarc.jsonc', '.git' },
  root_dir = function(bufnr, on_dir)
    local fname = vim.api.nvim_buf_get_name(bufnr)
    local markers = { '.luarc.json', '.luarc.jsonc', '.git' }
    local root = vim.fs.root(fname, markers)
    on_dir(root or vim.fn.getcwd())
  end,
})

vim.lsp.config('pyright', {
  cmd = { 'pyright-langserver', '--stdio' },
  filetypes = { 'python' },
  root_markers = { 'pyproject.toml', 'setup.py', 'setup.cfg', 'requirements.txt', '.git' },
  root_dir = function(bufnr, on_dir)
    local fname = vim.api.nvim_buf_get_name(bufnr)
    local markers = { 'pyproject.toml', 'setup.py', 'setup.cfg', 'requirements.txt', '.git' }
    local root = vim.fs.root(fname, markers)
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

vim.lsp.enable('rust_analyzer')
vim.lsp.enable("pyright")
vim.lsp.enable("lua_ls")
