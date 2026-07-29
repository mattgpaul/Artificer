-- Browser-based live markdown preview (pure Lua, no npm; renders the whole
-- .md file incl. mermaid via CDN libs).
return {
  "selimacerbas/markdown-preview.nvim",
  dependencies = { "selimacerbas/live-server.nvim" },
  ft = { "markdown" },
  cmd = { "MarkdownPreview", "MarkdownPreviewRefresh", "MarkdownPreviewStop" },
  keys = {
    { "<leader>mv", "<cmd>MarkdownPreview<cr>",        desc = "Markdown preview in browser (start)" },
    { "<leader>mr", "<cmd>MarkdownPreviewRefresh<cr>", desc = "Markdown preview refresh" },
    { "<leader>mx", "<cmd>MarkdownPreviewStop<cr>",    desc = "Markdown preview stop" },
  },
  config = function()
    require("markdown_preview").setup({
      instance_mode = "takeover",
      port = 0,
      open_browser = true,
      default_theme = "dark",
      debounce_ms = 300,
    })
  end,
}
