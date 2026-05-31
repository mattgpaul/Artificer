-- Minimal rtp so headless plenary can find the config's lua/ and plenary itself.
local cwd = vim.fn.getcwd()
vim.opt.rtp:prepend(cwd)
vim.opt.rtp:prepend(vim.fn.stdpath('data') .. '/lazy/plenary.nvim')
vim.cmd('runtime plugin/plenary.vim')
