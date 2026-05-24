return {
    {
    'windwp/nvim-autopairs',
    event = "InsertEnter",
    config = function()
        local npairs = require("nvim-autopairs")
        local Rule = require("nvim-autopairs.rule")
        npairs.setup()
        npairs.remove_rule("'")
        npairs.add_rule(Rule("'", "'"):with_pair(function()
            return vim.bo.filetype ~= "rust"
        end))
    end,
    }
}
