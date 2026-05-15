return {
    'nvim-telescope/telescope.nvim', version = '*',
    dependencies = {
        'nvim-lua/plenary.nvim',
        { 'nvim-telescope/telescope-fzf-native.nvim', build = 'make' },
    },
    opts = {
        defaults = {
            file_ignore_patterns = {
                'node_modules/', '%.git/', 'dist/', 'build/', 'target/',
                '%.next/', '__pycache__/', '%.venv/', 'venv/',
                '%.lock$', '%.log$',
            },
        },
    },
    keys = {
        { '<C-p>', '<cmd>Telescope find_files<cr>', desc = 'Find files' },
        { '<C-S-p>', '<cmd>Telescope live_grep<cr>', desc = 'Live grep' },
    },
}
