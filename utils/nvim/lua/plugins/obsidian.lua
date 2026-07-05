local vault = '/home/matthew/Documents/journal'

-- Open today's daily note in a vertical split (keeps whatever you were looking
-- at). The lcd autocmd below points Telescope/grep at the vault once we land.
local function open_today()
  vim.cmd('rightbelow vsplit')
  vim.cmd('Obsidian today')
end

-- Follow the wiki/markdown link under the cursor. If the target note doesn't
-- exist yet, create it silently with the configured template -- no prompt.
-- Falls back to LSP go-to-definition when the cursor isn't on a link.
local function follow_or_create()
  local obsidian = require('obsidian')
  local util = obsidian.util

  local link = obsidian.api.cursor_link()
  if not link then
    vim.lsp.buf.definition()
    return
  end

  local location = util.parse_link(link, { exclude = { 'Tag', 'BlockID' } })
  if not location or location == '' then
    vim.lsp.buf.definition()
    return
  end
  location = vim.uri_decode(location)

  -- External URLs open in the system browser.
  if util.is_uri(location) then
    vim.ui.open(location)
    return
  end

  -- Resolve against the vault, ignoring any #heading / ^block suffix.
  local query = util.strip_anchor_links(location)
  query = util.strip_block_links(query)

  local notes = obsidian.search.resolve_note(query)
  if notes and #notes > 0 then
    notes[1]:open()
  else
    require('obsidian.actions').new(query, function(note)
      note:open()
    end)
  end
end

return {
  -- Actively-maintained community fork (the original epwalsh/obsidian.nvim
  -- is archived). Uses the unified `:Obsidian <subcommand>` interface.
  'obsidian-nvim/obsidian.nvim',
  version = '*',
  ft = 'markdown',
  cmd = { 'Obsidian' },
  dependencies = {
    'nvim-lua/plenary.nvim',
  },

  keys = {
    -- The one keybind: open/create today's daily note.
    { '<leader>o', open_today, desc = 'Obsidian: today (daily note, split)' }, -- keybind: <leader>o|Obsidian: open/create today's daily note (split)
  },

  opts = {
    -- Only the new `:Obsidian <subcommand>` interface; no legacy aliases.
    legacy_commands = false,

    workspaces = {
      { name = 'journal', path = vault },
    },

    -- New non-daily notes land in the vault's `notes/` subdir.
    notes_subdir = 'notes',
    new_notes_location = 'notes_subdir',

    -- Template applied to any note created without an explicit template
    -- (e.g. `:Obsidian new` or following a link to a missing note).
    note = {
      template = 'note.md',
    },

    daily_notes = {
      folder = 'daily',
      date_format = '%Y-%m-%d',
      template = 'daily.md',
    },

    templates = {
      folder = 'templates',
      date_format = '%Y-%m-%d',
      time_format = '%H:%M',
    },

    -- obsidian.nvim manages the header so every note gets it automatically,
    -- however it's created (nvim, app, link-click).
    frontmatter = {
      -- Daily notes stay bare; everything else gets a managed header.
      enabled = function(fname)
        return not vim.startswith(fname, 'daily/')
      end,
      -- Runs on every save; reuses existing values so `created` doesn't churn.
      func = function(note)
        local meta = note.metadata or {}
        return {
          tags      = note.tags or {},
          backlinks = meta.backlinks or {},
          uplinks   = meta.uplinks or {},
          created   = meta.created or os.date('%Y-%m-%d %H:%M'),
        }
      end,
      sort = { 'tags', 'backlinks', 'uplinks', 'created' },
    },

    -- Filenames are the title verbatim (matches the Obsidian app), so a
    -- `[[Title]]` link stays `[[Title]]` instead of `[[title|Title]]`.
    note_id_func = function(title)
      if title ~= nil and title ~= '' then
        return title
      end
      return tostring(os.time())
    end,

    ui = { enable = true },
  },

  config = function(_, opts)
    require('obsidian').setup(opts)

    -- obsidian.nvim's inline UI relies on concealing; scope it to markdown
    -- so other filetypes are unaffected (and to silence the startup warning).
    vim.api.nvim_create_autocmd('FileType', {
      pattern = 'markdown',
      callback = function()
        vim.opt_local.conceallevel = 2
      end,
    })

    -- Whenever you land in a journal note, point this window's working
    -- directory at the vault (window-local, so your code windows are untouched)
    -- -- this is what makes Telescope find_files/live_grep search the notes.
    vim.api.nvim_create_autocmd('BufEnter', {
      pattern = '*.md',
      callback = function(args)
        if vim.startswith(vim.api.nvim_buf_get_name(args.buf), vault) then
          vim.cmd.lcd(vim.fn.fnameescape(vault))
        end
      end,
    })

    -- Override `gd` in markdown to follow/create links without the plugin's
    -- built-in "Create new note? Yes / Yes with Template / No" prompt. This
    -- autocmd is registered after the global LspAttach map (in lsp.lua), so
    -- the buffer-local map wins for markdown buffers.
    vim.api.nvim_create_autocmd('LspAttach', {
      callback = function(args)
        if vim.bo[args.buf].filetype ~= 'markdown' then
          return
        end
        vim.keymap.set('n', 'gd', follow_or_create, { -- keybind: gd|Obsidian markdown: follow link / create note, no prompt (overrides LSP gd)
          buffer = args.buf,
          desc = 'Obsidian: follow link / create note (no prompt)',
        })
      end,
    })
  end,
}
