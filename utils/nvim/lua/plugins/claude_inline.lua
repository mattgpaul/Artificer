-- claude_inline.lua — minimal Cmd-K-style inline edit driven by a local
-- llama.cpp server (llama-server).
--
-- Visual-select code, press <leader>k, type an instruction. The whole file is
-- POSTed to llama-server's OpenAI-compatible /v1/chat/completions endpoint with
-- the selected region marked, so the model can use the surrounding imports and
-- data structures as context; only the marked region is rewritten and then
-- replaced in place with the result, shown as an inline diff: new lines
-- highlighted green, removed lines rendered as red ghost lines above.
-- <leader>da accepts, <leader>dr rejects. No plugins, no API key — just a model
-- running locally (e.g. `task qwen3` from the Taskfile, which listens on :8080).

local M = {}

-- Where llama-server is listening. The Taskfile launches it on port 8080 with
-- the OpenAI-compatible API, so the chat-completions path lives under /v1.
-- llama-server serves whatever model was loaded at launch, so no model name is
-- sent in the request body.
M.config = {
    endpoint = 'http://localhost:8080/v1/chat/completions',
    temperature = 0.2,
}

local diff_ns = vim.api.nvim_create_namespace('claude_inline_diff')

-- Diff colors modelled on the Claude CLI: a soft green wash on added lines, a soft
-- red wash on removed lines, code text left readable. Defined explicitly (not linked
-- to DiffAdd/DiffDelete) so the colorscheme can't recolor them oddly. Re-applied on
-- ColorScheme so a theme switch doesn't clear them.
local function setup_highlights()
    vim.api.nvim_set_hl(0, 'ClaudeDiffAdd', { bg = '#1d5c2e', fg = '#e4ffe4' })
    vim.api.nvim_set_hl(0, 'ClaudeDiffDelete', { bg = '#5c1d1d', fg = '#ffe4e4' })
end

-- Strip a single leading/trailing markdown code fence, which `claude` often adds
-- even when told not to.
local function strip_fences(text)
    text = text:gsub('^%s*```%w*\n', '')
    text = text:gsub('\n```%s*$', '')
    return text
end

-- Render an inline diff over the just-applied change: the new lines (now in the
-- buffer at start_line..) get a green line highlight, and any removed lines are
-- shown as red ghost (virtual) lines above the spot they used to occupy. Then map
-- <leader>da to accept (clear the diff) and <leader>dr to reject (restore old_lines).
local function show_diff(bufnr, start_line, old_lines, new_lines)
    local hunks = vim.diff(
        table.concat(old_lines, '\n'),
        table.concat(new_lines, '\n'),
        { result_type = 'indices' }
    )

    vim.api.nvim_buf_clear_namespace(bufnr, diff_ns, 0, -1)

    if not hunks or vim.tbl_isempty(hunks) then
        vim.notify('Claude made no changes', vim.log.levels.INFO)
        return
    end

    for _, h in ipairs(hunks) do
        local sa, ca, sb, cb = h[1], h[2], h[3], h[4]

        -- Green-highlight the added/changed lines now sitting in the buffer.
        for k = 0, cb - 1 do
            local row = (start_line - 1) + (sb - 1) + k
            vim.api.nvim_buf_set_extmark(bufnr, diff_ns, row, 0, { line_hl_group = 'ClaudeDiffAdd' })
        end

        -- Removed lines become red ghost lines above where the change landed.
        if ca > 0 then
            local virt = {}
            for k = sa, sa + ca - 1 do
                virt[#virt + 1] = { { old_lines[k], 'ClaudeDiffDelete' } }
            end
            local row, above
            if cb > 0 then
                row, above = (start_line - 1) + (sb - 1), true
            elseif sb > 0 then
                -- Pure deletion: sb is the line after which content was removed.
                row, above = (start_line - 1) + (sb - 1), false
            else
                row, above = (start_line - 1), true
            end
            vim.api.nvim_buf_set_extmark(bufnr, diff_ns, row, 0, {
                virt_lines = virt,
                virt_lines_above = above,
            })
        end
    end

    local function finish()
        vim.api.nvim_buf_clear_namespace(bufnr, diff_ns, 0, -1)
        pcall(vim.keymap.del, 'n', '<leader>da', { buffer = bufnr })
        pcall(vim.keymap.del, 'n', '<leader>dr', { buffer = bufnr })
    end

    vim.keymap.set('n', '<leader>da', function()
        finish()
        vim.notify('Claude change accepted', vim.log.levels.INFO)
    end, { buffer = bufnr, desc = 'Claude: accept change' })

    vim.keymap.set('n', '<leader>dr', function()
        vim.api.nvim_buf_set_lines(bufnr, start_line - 1, start_line - 1 + #new_lines, false, old_lines)
        finish()
        vim.notify('Claude change rejected', vim.log.levels.INFO)
    end, { buffer = bufnr, desc = 'Claude: reject change' })

    vim.notify('Claude done — <leader>da accept · <leader>dr reject', vim.log.levels.INFO)
end

-- Pull the assistant's reply text out of an OpenAI-style chat-completions
-- response. Returns nil plus a message if the body isn't shaped as expected
-- (e.g. llama-server returned an error object instead of choices).
local function extract_content(raw)
    local ok, decoded = pcall(vim.json.decode, raw)
    if not ok or type(decoded) ~= 'table' then
        return nil, 'could not parse server response: ' .. raw
    end
    if decoded.error then
        local msg = type(decoded.error) == 'table' and decoded.error.message or tostring(decoded.error)
        return nil, 'server error: ' .. msg
    end
    local choice = decoded.choices and decoded.choices[1]
    local content = choice and choice.message and choice.message.content
    if not content then
        return nil, 'no completion in response: ' .. raw
    end
    return content
end

-- Markers that bracket the edit region inside the full-file context we send the
-- model. They give it a precise anchor for "which lines to rewrite" while still
-- seeing the rest of the file. The model is told not to echo them, but we also
-- strip them defensively from the reply (see strip_markers).
local EDIT_START = '<<<EDIT_REGION_START>>>'
local EDIT_END = '<<<EDIT_REGION_END>>>'

-- Drop any marker lines the model copied through, so they never land in the buffer.
local function strip_markers(text)
    local kept = {}
    for _, line in ipairs(vim.split(text, '\n', { plain = true })) do
        if line ~= EDIT_START and line ~= EDIT_END then
            kept[#kept + 1] = line
        end
    end
    return table.concat(kept, '\n')
end

-- Reproduce the whole buffer as a single string with the edit region wrapped in
-- markers, so the model can use the surrounding code (imports, types, helpers)
-- as context while knowing exactly which lines it's allowed to rewrite.
local function build_file_context(bufnr, start_line, end_line)
    local all = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
    local out = {}
    for i, line in ipairs(all) do
        if i == start_line then out[#out + 1] = EDIT_START end
        out[#out + 1] = line
        if i == end_line then out[#out + 1] = EDIT_END end
    end
    return table.concat(out, '\n')
end

-- Send the full file (with the edit region marked) + instruction to llama-server's
-- chat-completions endpoint and replace the range in place. The format guidance
-- goes in a system message and the file/instruction in a user message, which
-- instruct-tuned models follow more reliably than a single blob. on_done() is
-- called when the job finishes (success or failure) so the caller can tear down
-- its "working" indicator.
local function run_edit(bufnr, start_line, end_line, selection, filetype, instruction, on_done)
    local fname = vim.api.nvim_buf_get_name(bufnr)
    fname = fname ~= '' and vim.fn.fnamemodify(fname, ':~:.') or '[no name]'

    local body = vim.json.encode({
        messages = {
            {
                role = 'system',
                content = table.concat({
                    'You are a code editing assistant working inside an editor.',
                    'You are given the full contents of a file for context, with one',
                    'region bracketed by the markers ' .. EDIT_START .. ' and ' .. EDIT_END .. '.',
                    'Apply the user\'s instruction, rewriting ONLY the lines inside that',
                    'region. Use the rest of the file — imports, type and data-structure',
                    'definitions, surrounding helpers — to make the edit correct and',
                    'consistent with the codebase.',
                    'Output ONLY the replacement text for the marked region: no markers,',
                    'no explanation, no markdown fences, and nothing from outside the region.',
                    'Preserve the original indentation style.',
                }, ' '),
            },
            {
                role = 'user',
                content = table.concat({
                    'File: ' .. fname .. '  (language: ' .. (filetype ~= '' and filetype or 'unknown') .. ')',
                    '',
                    build_file_context(bufnr, start_line, end_line),
                    '',
                    'Rewrite only the lines between ' .. EDIT_START .. ' and ' .. EDIT_END .. '.',
                    'Instruction: ' .. instruction,
                }, '\n'),
            },
        },
        temperature = M.config.temperature,
        stream = false,
    })

    local stdout, stderr = {}, {}
    local job = vim.fn.jobstart({
        'curl', '-s', '-X', 'POST', M.config.endpoint,
        '-H', 'Content-Type: application/json',
        '--data', '@-',
    }, {
        stdout_buffered = true,
        stderr_buffered = true,
        on_stdout = function(_, data)
            if data then stdout = data end
        end,
        on_stderr = function(_, data)
            if data then stderr = data end
        end,
        on_exit = function(_, code)
            vim.schedule(function()
                if on_done then on_done() end
                if code ~= 0 then
                    vim.notify(
                        'llama-server request failed (curl exit ' .. code .. '). Is the server running?\n'
                        .. 'Start it with `task qwen3`.\n' .. table.concat(stderr, '\n'),
                        vim.log.levels.ERROR
                    )
                    return
                end
                local content, err = extract_content(table.concat(stdout, '\n'))
                if not content then
                    vim.notify('llama-server: ' .. err, vim.log.levels.ERROR)
                    return
                end
                local result = strip_markers(strip_fences(content))
                local new_lines = vim.split(result, '\n', { plain = true })
                local old_lines = vim.split(selection, '\n', { plain = true })
                vim.api.nvim_buf_set_lines(bufnr, start_line - 1, end_line, false, new_lines)
                show_diff(bufnr, start_line, old_lines, new_lines)
            end)
        end,
    })

    -- Hand the request body to curl over stdin so we never have to shell-escape
    -- the code (which can contain quotes, newlines, anything).
    if job <= 0 then
        if on_done then on_done() end
        vim.notify('could not start curl (is it installed?)', vim.log.levels.ERROR)
        return
    end
    vim.fn.chansend(job, body)
    vim.fn.chanclose(job, 'stdin')
end

-- Float a single-line input box just above the selection (or below it, when the
-- selection starts too near the top of the window to fit). Calls on_submit(text)
-- on <CR>, or closes silently on <Esc>.
local function open_prompt_window(start_line, end_line, on_submit)
    local origin_win = vim.api.nvim_get_current_win()
    local buf = vim.api.nvim_create_buf(false, true)
    vim.bo[buf].buftype = 'nofile'
    vim.bo[buf].bufhidden = 'wipe'

    local width = math.max(30, math.floor(vim.api.nvim_win_get_width(0) * 0.25))

    -- The bordered box is 3 rows tall (top border / input / bottom border).
    local cfg = {
        relative = 'win',
        col = 0,
        width = width,
        height = 1,
        style = 'minimal',
        border = 'rounded',
        title = ' claude ',
        title_pos = 'left',
    }
    if start_line - vim.fn.line('w0') >= 3 then
        -- Room above: lift the whole box so its bottom border clears the line.
        cfg.bufpos = { start_line - 1, 0 }
        cfg.row = -3
    else
        -- Top-of-window edge case: drop the box just below the selection instead.
        cfg.bufpos = { end_line - 1, 0 }
        cfg.row = 1
    end
    local win = vim.api.nvim_open_win(buf, true, cfg)
    vim.wo[win].winhl = 'Normal:Normal,FloatBorder:Comment'

    local spinner_timer

    local function close()
        if spinner_timer then
            spinner_timer:stop()
            spinner_timer:close()
            spinner_timer = nil
        end
        -- Only drop insert mode if the float still has focus (interactive cancel);
        -- when the job finishes you may be mid-edit in your own buffer — don't disturb.
        if vim.api.nvim_get_current_win() == win then
            vim.cmd('stopinsert')
        end
        if vim.api.nvim_win_is_valid(win) then
            vim.api.nvim_win_close(win, true)
        end
    end

    local function submit()
        local text = vim.api.nvim_buf_get_lines(buf, 0, 1, false)[1] or ''
        if text == '' then
            close()
            return
        end

        -- Turn the box into a non-interactive spinner and hand focus back to your
        -- buffer so you can keep working while Claude runs.
        vim.cmd('stopinsert')
        local frames = { '⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏' }
        local i = 1
        spinner_timer = vim.uv.new_timer()
        spinner_timer:start(0, 90, vim.schedule_wrap(function()
            if not vim.api.nvim_buf_is_valid(buf) then return end
            vim.api.nvim_buf_set_lines(buf, 0, 1, false, { ' ' .. frames[i] .. ' claude is working…' })
            i = i % #frames + 1
        end))
        if vim.api.nvim_win_is_valid(origin_win) then
            vim.api.nvim_set_current_win(origin_win)
        end

        on_submit(text, close)
    end

    vim.keymap.set({ 'n', 'i' }, '<CR>', submit, { buffer = buf })
    vim.keymap.set({ 'n', 'i' }, '<Esc>', close, { buffer = buf })
    vim.keymap.set('n', 'q', close, { buffer = buf })

    vim.cmd('startinsert')
end

local function inline_edit(start_line, end_line)
    local lines = vim.api.nvim_buf_get_lines(0, start_line - 1, end_line, false)
    local selection = table.concat(lines, '\n')
    local bufnr = vim.api.nvim_get_current_buf()
    local filetype = vim.bo.filetype

    open_prompt_window(start_line, end_line, function(instruction, on_done)
        run_edit(bufnr, start_line, end_line, selection, filetype, instruction, on_done)
    end)
end

function M.setup()
    setup_highlights()
    vim.api.nvim_create_autocmd('ColorScheme', { callback = setup_highlights })

    vim.keymap.set('x', '<leader>k', function()
        -- Leave visual mode first so the '< '> marks are committed.
        vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes('<Esc>', true, false, true), 'nx', false)
        inline_edit(vim.fn.line("'<"), vim.fn.line("'>"))
    end, { desc = 'Claude: inline edit selection' })

    vim.keymap.set('n', '<leader>k', function()
        local l = vim.fn.line('.')
        inline_edit(l, l)
    end, { desc = 'Claude: inline edit line' })
end

return {
    name = 'claude-inline',
    dir = vim.fn.stdpath('config'),
    lazy = false,
    config = function() M.setup() end,
}
