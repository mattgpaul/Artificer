-- claude_inline.lua — minimal Cmd-K-style inline edit driven by a local
-- llama.cpp server (llama-server).
--
-- Visual-select code, press <leader>kk, type an instruction. Only the selected
-- region is POSTed to llama-server's OpenAI-compatible /v1/chat/completions
-- endpoint, together with the definitions it references — pulled deterministically
-- from the language servers (see gather_lsp_context) — so the edit stays strictly
-- bounded to your selection while still being aware of cross-file types and the
-- public API of imported dependencies. The region is rewritten and replaced in
-- place with the result, shown as an inline diff: new lines
-- highlighted green, removed lines rendered as red ghost lines above.
-- <leader>da accepts, <leader>dr rejects. No plugins, no API key — just a model
-- running locally (e.g. `task qwen3` from the Taskfile, which listens on :8080).
--
-- <leader>k is a chord prefix. <leader>kk opens the interactive prompt (above);
-- the visual one-shot presets skip the prompt and fire a canned instruction:
-- <leader>ki implement · <leader>kd document · <leader>kr refactor ·
-- <leader>kf fix · <leader>kp improve performance. See M.config.presets.

local M = {}

-- Where llama-server is listening. The Taskfile launches it on port 8080 with
-- the OpenAI-compatible API, so the chat-completions path lives under /v1.
-- llama-server serves whatever model was loaded at launch, so no model name is
-- sent in the request body.
M.config = {
    endpoint = 'http://localhost:8080/v1/chat/completions',
    temperature = 0.2,
    -- Deterministic LSP-driven context: before an edit, resolve the definitions the
    -- selected region (and any imported dependency the instruction names) references,
    -- and inject them into the prompt so the model edits against real signatures rather
    -- than guesses. Budgets below are the only guard against context blowup; lower them
    -- if the local model's window feels tight. Set enabled = false for the old behavior.
    lsp_context = {
        enabled     = true,
        max_symbols = 24,   -- unique seed identifiers we hover
        max_blocks  = 12,   -- distinct context blocks injected (after content-dedupe)
        max_members = 16,   -- public signatures listed when surfacing a dependency's API
        max_lines   = 160,  -- hard cap on total injected context lines
        deadline_ms = 2000, -- max time we wait for LSP before sending without it
    },
    -- One-shot visual presets: <leader>k<key> in visual mode fires the canned
    -- instruction below against the selection with no prompt box — for the cases
    -- where you'd just type the same thing every time. Each flows through the
    -- normal LSP-gather + inline-diff path; only the instruction is fixed.
    presets = {
        {
            key = 'i', desc = 'implement selection',
            instruction = 'Implement the selected code using the surrounding context, the declared types/signatures, and the referenced definitions provided. Replace the selection with a complete, working implementation. Keep any existing signature unchanged unless it is an incomplete stub.',
        },
        {
            key = 'd', desc = 'document selection',
            instruction = 'Add idiomatic doc comments to the selected code. Do not change its logic, signatures, or behavior — only add documentation.',
        },
        {
            key = 'r', desc = 'refactor / simplify',
            instruction = 'Refactor the selected code to be cleaner and more idiomatic for its language while preserving its exact behavior and public signature.',
        },
        {
            key = 'f', desc = 'fix / debug',
            instruction = 'Find and fix any bugs in the selected code. Preserve its intent and signature; output only the corrected code.',
        },
        {
            key = 'p', desc = 'improve performance',
            instruction = 'Improve the performance of the selected code: prefer stack allocation over heap, avoid unnecessary allocations/clones, and keep behavior and signatures unchanged.',
        },
    },
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
            -- Clamp into range: a deletion at end-of-buffer can leave `row` past the
            -- last line, which set_extmark would reject.
            row = math.max(0, math.min(row, vim.api.nvim_buf_line_count(bufnr) - 1))
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


-- ─── LSP context gathering ────────────────────────────────────────────────────
-- Everything below resolves, via the editor's own language servers, the definitions
-- the edit region references — including the public API surface of imported
-- dependencies — and renders them as a compact, read-only context block. This is the
-- same index the IDE reads to autocomplete and show signatures; no model is in the
-- gathering loop, and every query is driven by fixed rules over a bounded seed set, so
-- it stays deterministic and can't balloon the prompt.

-- Common keywords that are never worth a hover request (they resolve to nothing).
local STOPWORDS = {
    ['let'] = true, ['fn'] = true, ['pub'] = true, ['mut'] = true, ['self'] = true,
    ['Self'] = true, ['return'] = true, ['if'] = true, ['else'] = true, ['match'] = true,
    ['for'] = true, ['while'] = true, ['loop'] = true, ['in'] = true, ['impl'] = true,
    ['struct'] = true, ['enum'] = true, ['trait'] = true, ['use'] = true, ['as'] = true,
    ['const'] = true, ['static'] = true, ['type'] = true, ['where'] = true, ['async'] = true,
    ['await'] = true, ['move'] = true, ['ref'] = true, ['true'] = true, ['false'] = true,
    ['def'] = true, ['class'] = true, ['import'] = true, ['from'] = true, ['and'] = true,
    ['or'] = true, ['not'] = true, ['None'] = true, ['True'] = true, ['False'] = true,
    ['the'] = true, ['api'] = true, ['to'] = true, ['use'] = true,
}

-- Normalize an LSP hover `contents` payload (MarkupContent / MarkedString / array) into
-- a trimmed plain string, dropping markdown code fences so we keep the signature text.
local function markup_to_string(contents)
    if not contents then return nil end
    local ok, lines = pcall(vim.lsp.util.convert_input_to_markdown_lines, contents)
    if not ok or type(lines) ~= 'table' then
        if type(contents) == 'string' then
            lines = vim.split(contents, '\n', { plain = true })
        elseif type(contents) == 'table' and contents.value then
            lines = vim.split(contents.value, '\n', { plain = true })
        else
            return nil
        end
    end
    local kept = {}
    for _, l in ipairs(lines) do
        if not l:match('^%s*```') then kept[#kept + 1] = l end
    end
    local s = vim.trim(table.concat(kept, '\n'))
    return s ~= '' and s or nil
end

-- Pull the first usable target URI out of a textDocument/definition response, which may
-- be a Location, a LocationLink (targetUri), or an array of either, per client.
local function first_location_uri(results)
    for _, res in pairs(results or {}) do
        local r = res.result
        if type(r) == 'table' then
            if r.uri then return r.uri end
            if r.targetUri then return r.targetUri end
            if r[1] then return r[1].uri or r[1].targetUri end
        end
    end
    return nil
end

-- Tier-2 surface: given a dependency/type's definition file, extract its callable
-- signatures (the "what can I call on this" list) by reading the file directly — no
-- second LSP round trip, so it works for registry/site-packages files without a didOpen
-- dance. Captures every fn/method, not just `pub fn`, because trait-impl methods (the
-- ones a refactor most often needs) are not `pub`; and it accumulates multi-line
-- signatures so wrapped parameter lists survive. Bounded by max_members.
local function extract_member_signatures(uri, max_members)
    local path = vim.uri_to_fname(uri)
    local ok, lines = pcall(vim.fn.readfile, path)
    if not ok or type(lines) ~= 'table' then return nil end
    local sigs, seen = {}, {}
    local function push(sig)
        sig = vim.trim(sig)
        if sig ~= '' and not seen[sig] then
            seen[sig] = true
            sigs[#sigs + 1] = sig
        end
    end

    if path:match('%.py$') then
        for _, l in ipairs(lines) do
            local d = l:match('^%s*def%s+[%w_]+%b()')
                or l:match('^%s*async%s+def%s+[%w_]+%b()')
                or l:match('^%s*class%s+[%w_]+')
            if d then push(d) end
            if #sigs >= max_members then break end
        end
        if vim.tbl_isempty(sigs) then return nil end
        return table.concat(sigs, '\n')
    end

    -- Rust (and C-like): a signature starts at a standalone `fn <name>` whose prefix is
    -- only modifiers (pub / async / const / unsafe / pub(crate) …). Accumulate following
    -- lines until the parameter parens balance and we reach the body `{` or trait-decl `;`.
    local i, n = 1, #lines
    while i <= n and #sigs < max_members do
        local pre, name = lines[i]:match('^(.-)%f[%a]fn%f[%A]%s+([%w_]+)')
        if pre and name and pre:match('^[%s%w_(),]*$') then
            local parts, depth, terminated, j = {}, 0, false, i
            while j <= n and j - i <= 12 do
                local s = lines[j]
                parts[#parts + 1] = vim.trim(s)
                for ch in s:gmatch('[%(%)]') do depth = depth + (ch == '(' and 1 or -1) end
                if depth <= 0 and (s:find('{', 1, true) or s:find(';', 1, true)) then
                    terminated = true
                    break
                end
                j = j + 1
            end
            if terminated then
                local sig = table.concat(parts, ' '):gsub('%s*{.*$', ''):gsub('%s*;%s*$', '')
                push(sig)
                i = j + 1
            else
                i = i + 1
            end
        else
            i = i + 1
        end
    end
    if vim.tbl_isempty(sigs) then return nil end
    return table.concat(sigs, '\n')
end

-- First whole-identifier position (0-indexed row, col) of `word` anywhere in `all_lines`,
-- so an instruction token like "yahoo" gets a real buffer anchor to query the server at.
local function find_word_position(all_lines, word)
    for r, line in ipairs(all_lines) do
        local s = 1
        while true do
            local a, b = line:find('[%a_][%w_]*', s)
            if not a then break end
            if line:sub(a, b) == word then return r - 1, a - 1 end
            s = b + 1
        end
    end
    return nil
end

-- Build the bounded seed set: the symbols we will ask the server about. Three sources so a
-- dependency named only in the instruction still resolves: (a) identifiers in the region,
-- (b) identifiers on the file's import/use lines, (c) instruction tokens that also occur in
-- the buffer. Each seed records a real {row,col} anchor and whether it's "intentional"
-- (named in the instruction or used in the region) — only those get Tier-2 API expansion.
local function collect_seeds(bufnr, start_line, end_line, instruction, max_symbols)
    local all = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)

    local region_words, instr_words = {}, {}
    for r = start_line, end_line do
        for w in (all[r] or ''):gmatch('[%a_][%w_]*') do region_words[w] = true end
    end
    for w in (instruction or ''):gmatch('[%a_][%w_]*') do instr_words[w] = true end

    local seeds, seen = {}, {}
    local function add_word(word, row, col)
        if seen[word] or STOPWORDS[word] or #word < 2 or #seeds >= max_symbols then return end
        seen[word] = true
        seeds[#seeds + 1] = {
            word = word, row = row, col = col,
            intentional = (region_words[word] or instr_words[word]) or false,
        }
    end
    local function scan_line(r)
        local line = all[r]
        if not line then return end
        local s = 1
        while #seeds < max_symbols do
            local a, b = line:find('[%a_][%w_]*', s)
            if not a then break end
            add_word(line:sub(a, b), r - 1, a - 1)
            s = b + 1
        end
    end

    -- (a) region
    for r = start_line, end_line do scan_line(r) end
    -- (b) import / use lines
    for r, line in ipairs(all) do
        if line:match('^%s*use%s') or line:match('^%s*import%s') or line:match('^%s*from%s.+import') then
            scan_line(r)
        end
    end
    -- (c) instruction tokens present in the buffer
    for w in (instruction or ''):gmatch('[%a_][%w_]*') do
        if not seen[w] and not STOPWORDS[w] and #w >= 2 then
            local row, col = find_word_position(all, w)
            if row then add_word(w, row, col) end
        end
    end

    return seeds
end

-- Render collected context blocks into the read-only string injected into the prompt,
-- enforcing the block/line budgets so even a large dependency stays bounded.
local function assemble_context(blocks, cfg)
    if vim.tbl_isempty(blocks) then return nil end
    local out = {
        'Referenced definitions & dependency APIs (from LSP — context only, do NOT modify or reproduce these):',
    }
    local nlines, nblocks = 1, 0
    for _, b in ipairs(blocks) do
        if nblocks >= cfg.max_blocks or nlines >= cfg.max_lines then break end
        local seg = { '--- ' .. b.title .. ' ---' }
        for _, l in ipairs(vim.split(b.body, '\n', { plain = true })) do seg[#seg + 1] = l end
        if nlines + #seg > cfg.max_lines then
            seg = vim.list_slice(seg, 1, math.max(1, cfg.max_lines - nlines))
            seg[#seg + 1] = '… (truncated)'
        end
        for _, l in ipairs(seg) do out[#out + 1] = l end
        out[#out + 1] = ''
        nlines = nlines + #seg + 1
        nblocks = nblocks + 1
    end
    return table.concat(out, '\n')
end

-- Tier-2 for one intentional seed: resolve its definition, then read that file for the
-- dependency's public signatures. Calls finish() exactly once when done (success or not).
local function request_member_surface(bufnr, sd, pos_params, max_members, add_block, finish)
    vim.lsp.buf_request_all(bufnr, 'textDocument/definition', pos_params(sd.row, sd.col), function(dres)
        local uri = first_location_uri(dres)
        if uri then
            local members = extract_member_signatures(uri, max_members)
            if members then add_block(sd.word .. ' — api surface', members) end
        end
        finish()
    end)
end

-- Gather LSP context asynchronously and hand the assembled string (or nil) to on_ready.
-- Tier 1 hovers every seed for its signature/type; Tier 2 expands the API surface of the
-- intentional seeds. on_ready fires once every request returns OR the deadline elapses,
-- whichever comes first, so a cold server or unindexed dependency can never hang the edit.
local function gather_lsp_context(bufnr, start_line, end_line, instruction, on_ready)
    local cfg = M.config.lsp_context
    if not cfg.enabled
        or vim.api.nvim_buf_get_name(bufnr) == ''
        or vim.tbl_isempty(vim.lsp.get_clients({ bufnr = bufnr })) then
        return on_ready(nil)
    end

    local seeds = collect_seeds(bufnr, start_line, end_line, instruction, cfg.max_symbols)
    if vim.tbl_isempty(seeds) then return on_ready(nil) end

    local blocks, block_keys = {}, {}
    local function add_block(title, body)
        if not body or body == '' or block_keys[body] then return end
        block_keys[body] = true
        blocks[#blocks + 1] = { title = title, body = body }
    end

    local pending, finished = 1, false
    local function finalize()
        if finished then return end
        finished = true
        on_ready(assemble_context(blocks, cfg))
    end
    local function done_one()
        pending = pending - 1
        if pending <= 0 then finalize() end
    end

    local function pos_params(row, col)
        return {
            textDocument = vim.lsp.util.make_text_document_params(bufnr),
            position = { line = row, character = col },
        }
    end

    for _, sd in ipairs(seeds) do
        -- Tier 1: hover for the signature/type of every seed.
        pending = pending + 1
        vim.lsp.buf_request_all(bufnr, 'textDocument/hover', pos_params(sd.row, sd.col), function(results)
            local body
            for _, res in pairs(results or {}) do
                if res.result and res.result.contents then
                    body = markup_to_string(res.result.contents)
                    if body then break end
                end
            end
            add_block(sd.word, body)
            done_one()
        end)
        -- Tier 2: dependency API surface, only for intentional seeds.
        if sd.intentional then
            pending = pending + 1
            request_member_surface(bufnr, sd, pos_params, cfg.max_members, add_block, done_one)
        end
    end

    done_one()                           -- release the issuing guard
    vim.defer_fn(finalize, cfg.deadline_ms)
end

-- Markers that delimit the edit region inside the full-file context. Chosen as
-- guillemets so they essentially never collide with real source tokens.
local EDIT_START = '«EDIT_START»'
local EDIT_END   = '«EDIT_END»'

-- Build the system + user chat messages for one inline edit. PURE: it takes only
-- plain values (no buffer handle, no LSP, no network) and returns the exact message
-- list run_edit will POST. That purity is the whole point — it's what the tests pin
-- down, so we can prove the model receives the entire file with the region marked.
--   opts = { fname, filetype, lines (full buffer, 1-indexed list),
--            start_line, end_line (inclusive), instruction, visual, lsp_ctx }
function M.build_messages(opts)
    local region = opts.visual and 'selected region' or 'cursor line'
    local system = table.concat({
        'You are a code editing assistant working inside an editor.',
        'You are given a COMPLETE source file for context. The ' .. region .. ' the user',
        'wants changed is delimited by ' .. EDIT_START .. ' and ' .. EDIT_END .. ' markers.',
        'You may also be given read-only reference definitions from the codebase.',
        (opts.visual
            and 'Rewrite ONLY the code between the markers according to the instruction.'
            or  'Apply the instruction at the marked line: you may rewrite it and/or insert new lines in its place.'),
        'Output ONLY the code that should replace the marked region: no explanation,',
        'no markdown fences, no markers, and nothing besides that code.',
        'Do NOT output the rest of the file. Preserve the original indentation style.',
        (opts.visual and 'If the instruction asks to remove the code, output nothing.' or ''),
    }, ' ')

    -- Reconstruct the file with markers wrapping the edit region.
    local marked = {}
    for i, line in ipairs(opts.lines) do
        if i == opts.start_line then marked[#marked + 1] = EDIT_START end
        marked[#marked + 1] = line
        if i == opts.end_line then marked[#marked + 1] = EDIT_END end
    end

    local parts = {
        'File: ' .. opts.fname .. '  (language: ' .. (opts.filetype ~= '' and opts.filetype or 'unknown') .. ')',
        '',
        'Full file (edit the region between ' .. EDIT_START .. ' and ' .. EDIT_END .. '):',
        table.concat(marked, '\n'),
        '',
    }
    if opts.lsp_ctx and opts.lsp_ctx ~= '' then
        parts[#parts + 1] = opts.lsp_ctx
        parts[#parts + 1] = ''
    end
    parts[#parts + 1] = 'Instruction: ' .. opts.instruction

    return {
        { role = 'system', content = system },
        { role = 'user',   content = table.concat(parts, '\n') },
    }
end

-- Send the full file (with the edit region marked) + instruction to llama-server's
-- chat-completions endpoint and replace the range in place. The prompt itself is
-- built by the pure M.build_messages; this function only handles buffer I/O and the
-- async curl job. on_done() is called when the job finishes (success or failure) so
-- the caller can tear down its "working" indicator.
local function run_edit(bufnr, start_line, end_line, selection, filetype, instruction, visual, lsp_ctx, on_done)
    local fname = vim.api.nvim_buf_get_name(bufnr)
    fname = fname ~= '' and vim.fn.fnamemodify(fname, ':~:.') or '[no name]'

    local lines = vim.api.nvim_buf_get_lines(bufnr, 0, -1, false)
    local messages = M.build_messages({
        fname       = fname,
        filetype    = filetype,
        lines       = lines,
        start_line  = start_line,
        end_line    = end_line,
        instruction = instruction,
        visual      = visual,
        lsp_ctx     = lsp_ctx,
    })

    local body = vim.json.encode({
        messages    = messages,
        temperature = M.config.temperature,
        stream      = false,
    })

    -- Keep the last request around so :lua require('claude_inline').dump_last()
    -- can show exactly what the model received — the determinism handle.
    M._last_request = { messages = messages, body = body }

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
                local result = strip_fences(content)
                local old_lines = vim.split(selection, '\n', { plain = true })
                -- An empty reply means "remove this code": drop the lines entirely
                -- rather than leaving a blank line behind.
                local new_lines = vim.trim(result) == '' and {} or vim.split(result, '\n', { plain = true })
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
-- on <CR>, or closes silently on <Esc>. When `preset` is given the input box is
-- skipped entirely: the float is created straight as the spinner and the preset
-- instruction is submitted immediately (used by the visual one-shot hotkeys).
local function open_prompt_window(start_line, end_line, on_submit, preset)
    local origin_win = vim.api.nvim_get_current_win()
    local buf = vim.api.nvim_create_buf(false, true)
    vim.bo[buf].buftype = 'nofile'
    vim.bo[buf].bufhidden = 'wipe'

    local width = math.max(50, math.floor(vim.api.nvim_win_get_width(0) * 0.5))

    -- The bordered box is 3 rows tall (top border / input / bottom border).
    local cfg = {
        relative = 'win',
        col = 0,
        width = width,
        height = 1,
        style = 'minimal',
        border = 'rounded',
        title = ' ⦇⌐■_■⦆ cerebro ',
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

    local function submit(forced_text)
        local text = forced_text or vim.api.nvim_buf_get_lines(buf, 0, 1, false)[1] or ''
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
            vim.api.nvim_buf_set_lines(buf, 0, 1, false, { ' ' .. frames[i] .. ' cerebro is working…' })
            i = i % #frames + 1
        end))
        if vim.api.nvim_win_is_valid(origin_win) then
            vim.api.nvim_set_current_win(origin_win)
        end

        on_submit(text, close)
    end

    if preset then
        -- One-shot: no input, no insert mode — go straight to the spinner and run.
        submit(preset)
        return
    end

    vim.keymap.set({ 'n', 'i' }, '<CR>', function() submit() end, { buffer = buf })
    vim.keymap.set({ 'n', 'i' }, '<Esc>', close, { buffer = buf })
    vim.keymap.set('n', 'q', close, { buffer = buf })

    vim.cmd('startinsert')
end

local function inline_edit(start_line, end_line, visual, preset)
    local lines = vim.api.nvim_buf_get_lines(0, start_line - 1, end_line, false)
    local selection = table.concat(lines, '\n')
    local bufnr = vim.api.nvim_get_current_buf()
    local filetype = vim.bo.filetype

    open_prompt_window(start_line, end_line, function(instruction, on_done)
        -- Gather LSP context (signatures of referenced symbols + named-dependency API
        -- surfaces) while the spinner runs, then send the enriched prompt. The gather has
        -- its own deadline, so this never stalls if a server is cold.
        gather_lsp_context(bufnr, start_line, end_line, instruction, function(lsp_ctx)
            run_edit(bufnr, start_line, end_line, selection, filetype, instruction, visual, lsp_ctx, on_done)
        end)
    end, preset)
end

-- Write the last request body to a file (default /tmp) so you can read precisely
-- what was sent — full file, markers, LSP context, instruction — and confirm the
-- context is complete rather than guessing from garbage output.
function M.dump_last(path)
    if not M._last_request then
        vim.notify('claude_inline: no request captured yet', vim.log.levels.WARN)
        return
    end
    path = path or '/tmp/claude_inline_last.json'
    vim.fn.writefile(vim.split(M._last_request.body, '\n', { plain = true }), path)
    vim.notify('claude_inline: wrote last request to ' .. path, vim.log.levels.INFO)
    return M._last_request
end

function M.setup()
    setup_highlights()
    vim.api.nvim_create_autocmd('ColorScheme', { callback = setup_highlights })

    -- <leader>k is a chord prefix: <leader>kk opens the interactive prompt; the
    -- preset keys below fire a canned instruction with no prompt box.
    vim.keymap.set('x', '<leader>kk', function()
        -- Leave visual mode first so the '< '> marks are committed.
        vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes('<Esc>', true, false, true), 'nx', false)
        inline_edit(vim.fn.line("'<"), vim.fn.line("'>"), true)
    end, { desc = 'Claude: inline edit selection (prompt)' })

    vim.keymap.set('n', '<leader>kk', function()
        local l = vim.fn.line('.')
        inline_edit(l, l, false)
    end, { desc = 'Claude: inline edit line (prompt)' })

    -- Visual-only one-shot presets: <leader>k<key> → canned instruction, no prompt.
    for _, p in ipairs(M.config.presets) do
        vim.keymap.set('x', '<leader>k' .. p.key, function()
            vim.api.nvim_feedkeys(vim.api.nvim_replace_termcodes('<Esc>', true, false, true), 'nx', false)
            inline_edit(vim.fn.line("'<"), vim.fn.line("'>"), true, p.instruction)
        end, { desc = 'Claude: ' .. p.desc })
    end
end

-- `require('plugins.claude_inline')` returns the lazy spec below; the implementation
-- table is registered here so tests/REPL can reach it via require('claude_inline').
package.loaded['claude_inline'] = M

return {
    name = 'claude-inline',
    dir = vim.fn.stdpath('config'),
    lazy = false,
    config = function() M.setup() end,
}
