return
{
	'nvim-treesitter/nvim-treesitter',
	lazy = false,
	build = ':TSUpdate',
	opts = {
		ensure_installed = {
			"lua",
			"python",
			"rust",
			"c",
			"bash",
			"json",
			"yaml",
			"markdown",
		},
		highlight = {
			enable = true,
		},
	},
}
