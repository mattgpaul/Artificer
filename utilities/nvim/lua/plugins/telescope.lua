return {
    'nvim-telescope/telescope.nvim', version = '*',
    dependencies = {
        'nvim-lua/plenary.nvim',
        -- optional but recommended
        { 'nvim-telescope/telescope-fzf-native.nvim', build = 'make' },
    },
    keys = {
        { '<D-p>', '<cmd>Telescope find_files<cr>', desc = 'Find files' },
        { '<D-h>', '<cmd>Telescope live_grep<cr>', desc = 'Live grep' },
    },
}
