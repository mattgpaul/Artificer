vim.keymap.set('n', '<M-b>', vim.cmd.Ex, { desc = 'Open netrw' })

-- Markdown timestamp insertion
vim.api.nvim_create_autocmd('FileType', {
  pattern = 'markdown',
  callback = function(args)

    -- <leader>td : date only  (e.g. 2026-06-03)
    vim.keymap.set('n', '<leader>td', function()
      vim.api.nvim_put({ os.date('%Y-%m-%d') }, '', true, true)
    end, { buffer = args.buf, desc = 'Insert timestamp (date)' })

    -- <leader>ts : date + time (e.g. 2026-06-03 14:32:07)
    vim.keymap.set('n', '<leader>ts', function()
      vim.api.nvim_put({ os.date('%Y-%m-%d %H:%M:%S') }, '', true, true)
    end, { buffer = args.buf, desc = 'Insert timestamp (date + time)' })
  end,
})
