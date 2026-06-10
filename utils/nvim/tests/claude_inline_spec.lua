require('plugins.claude_inline')              -- run the file → registers the impl
local M = package.loaded['claude_inline']

local function read_fixture()
    local path = vim.fn.getcwd() .. '/tests/fixtures/sample.rs'
    return vim.fn.readfile(path)               -- list of lines, 1-indexed
end

describe('build_messages', function()
    local lines = read_fixture()

    it('includes the entire file, not just the selection', function()
        local msgs = M.build_messages({
            fname = 'sample.rs', filetype = 'rust', lines = lines,
            start_line = 5, end_line = 7, visual = true,
            instruction = 'make beta add two',
        })
        local user = msgs[2].content
        for _, l in ipairs(lines) do
            if l ~= '' then
                assert.is_truthy(user:find(l, 1, true), 'missing file line: ' .. l)
            end
        end
    end)

    it('wraps exactly the selected region in markers', function()
        local msgs = M.build_messages({
            fname = 'sample.rs', filetype = 'rust', lines = lines,
            start_line = 5, end_line = 7, visual = true,
            instruction = 'x',
        })
        local out = vim.split(msgs[2].content, '\n', { plain = true })
        local si, ei
        for i, l in ipairs(out) do
            if l == '«EDIT_START»' then si = i end
            if l == '«EDIT_END»'   then ei = i end
        end
        assert.are.equal(out[si + 1], lines[5])   -- first marked line == region start
        assert.are.equal(out[ei - 1], lines[7])   -- last marked line == region end
    end)

    it('omits LSP context when none is provided, includes it when given', function()
        local without = M.build_messages({
            fname = 'f', filetype = 'rust', lines = lines,
            start_line = 1, end_line = 1, visual = false, instruction = 'x',
        })
        assert.is_nil(without[2].content:find('Referenced definitions', 1, true))

        local with = M.build_messages({
            fname = 'f', filetype = 'rust', lines = lines,
            start_line = 1, end_line = 1, visual = false, instruction = 'x',
            lsp_ctx = 'Referenced definitions & dependency APIs:\n--- beta ---\nfn beta(x: i32) -> i32',
        })
        assert.is_truthy(with[2].content:find('fn beta(x: i32) -> i32', 1, true))
    end)

    it('always carries the instruction', function()
        local msgs = M.build_messages({
            fname = 'f', filetype = 'rust', lines = lines,
            start_line = 1, end_line = 1, visual = false, instruction = 'rename to delta',
        })
        assert.is_truthy(msgs[2].content:find('Instruction: rename to delta', 1, true))
    end)
end)
