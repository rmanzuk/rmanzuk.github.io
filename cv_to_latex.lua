-- Pandoc Lua filter: converts cv.md HTML blocks → LaTeX matching the original CV style.
-- Only active when the output format is latex/pdf.

local function to_latex(s)
  s = s:gsub("\n", " "):gsub("%s+", " ")
  -- HTML entities
  s = s:gsub("&amp;",  "\\&")
  s = s:gsub("&lt;",   "<")
  s = s:gsub("&gt;",   ">")
  s = s:gsub("&nbsp;", "~")
  -- Inline formatting
  s = s:gsub("<strong>(.-)</strong>", "\\textbf{%1}")
  s = s:gsub("<b>(.-)</b>",           "\\textbf{%1}")
  s = s:gsub("<em>(.-)</em>",         "\\textit{%1}")
  s = s:gsub("<i>(.-)</i>",           "\\textit{%1}")
  s = s:gsub("<small>(.-)</small>",   "{\\small %1}")
  -- Links
  s = s:gsub('<a[^>]+href="([^"]+)"[^>]*>(.-)</a>', "\\href{%1}{%2}")
  -- Line breaks inside table cells
  s = s:gsub("<br%s*/?>%s*", "\\newline ")
  -- Strip remaining tags
  s = s:gsub("<[^>]+>", "")
  -- Unicode → LaTeX (safety for all engines)
  s = s:gsub("→", "$\\rightarrow$")
  s = s:gsub("×", "$\\times$")
  return s:match("^%s*(.-)%s*$")
end

local function parse_cv_table(html)
  -- Flatten so Lua patterns work across original line breaks
  local flat = html:gsub("\n", " "):gsub("%s+", " ")
  local rows = {}
  for row in flat:gmatch("<tr>(.-)</tr>") do
    local tds = {}
    for cell in row:gmatch("<td[^>]*>(.-)</td>") do
      table.insert(tds, cell)
    end
    if #tds >= 2 then
      table.insert(rows, { date = to_latex(tds[1]), content = to_latex(tds[2]) })
    end
  end

  -- Column spec: fixed-width right-aligned date column (matches original r|m layout)
  local colspec = ">{{\\raggedleft\\arraybackslash}}p{{2.5cm}}|X"
  local lines = {
    "\\vspace{0.3em}",
    "\\begin{tabularx}{\\linewidth}{" .. colspec .. "}",
  }
  for i, row in ipairs(rows) do
    -- Add a vertical strut before each row after the first (matches \rule{0pt}{3ex})
    local prefix = (i > 1) and "\\rule{0pt}{2.5ex}" or ""
    lines[#lines + 1] = "  " .. prefix .. row.date .. " & " .. row.content .. " \\\\"
  end
  lines[#lines + 1] = "\\end{tabularx}"
  return table.concat(lines, "\n")
end

function RawBlock(el)
  if el.format ~= "html" then return end
  local s = el.text

  -- cv-table → tabularx
  if s:match('class="cv%-table"') then
    return pandoc.RawBlock("latex", parse_cv_table(s))
  end

  -- Centered header div (pure HTML, no internal blank lines)
  if s:match("text%-align%s*:%s*center") then
    local flat = s:gsub("\n", " "):gsub("%s+", " ")
    local inner = flat:match("<div[^>]*>(.-)</div>")
    if inner then
      return pandoc.RawBlock("latex",
        "\\begin{center}\n" .. to_latex(inner) .. "\n\\end{center}")
    end
  end

  -- Download-PDF link → omit from PDF
  if s:match("Download PDF") or s:match("%↓") then
    return pandoc.RawBlock("latex", "")
  end

  -- Standalone <small> block (publication footnote)
  if s:match("<small>") then
    local flat = s:gsub("\n", " ")
    local inner = flat:match("<small>(.-)</small>") or ""
    return pandoc.RawBlock("latex", "{\\small " .. to_latex(inner) .. "}\n")
  end

  -- Stray opening/closing div tags (from mixed markdown/HTML blocks) → ignore
  if s:match("^%s*</?div") then
    return pandoc.RawBlock("latex", "")
  end

  -- Fallback: strip tags
  return pandoc.RawBlock("latex", s:gsub("<[^>]+>", ""))
end

-- Section headings: small-caps title + horizontal rule, matching the original LaTeX
function Header(el)
  if el.level == 2 and FORMAT == "latex" then
    local title = pandoc.utils.stringify(el)
    return pandoc.RawBlock("latex", table.concat({
      "",
      "\\vspace{-0.2em}",
      "\\begin{flushleft}\\textsc{" .. title .. "}\\end{flushleft}",
      "\\vspace{-1em}",
      "\\noindent\\makebox[\\linewidth]{\\rule{\\textwidth}{0.4pt}}",
      "",
    }, "\n"))
  end
end

-- Drop horizontal rules (---) in PDF; section rules come from the Header filter above
function HorizontalRule(el)
  if FORMAT == "latex" then
    return pandoc.RawBlock("latex", "")
  end
end
