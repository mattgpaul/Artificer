return {
	{
		'akinsho/toggleterm.nvim',
		version = "*",
		opts = {
			direction = 'float',
			float_opts = {
				border = 'curved',
				width = function()
					return vim.o.columns
				end,
				height = function()
					return vim.o.lines
				end,
			},
			open_mapping = [[<M-j>]],
		},
		config = function(_, opts)
			require("toggleterm").setup(opts)
			
			-- Terminal mode mapping to close with Alt+j
			vim.keymap.set('t', '<M-j>', [[<C-\><C-n>:ToggleTerm<CR>]], { desc = 'Toggle terminal' })
		end,
	}
}

