#!/usr/bin/env python3
"""
Preprocess cv.md for pandoc PDF generation.

Reads cv.md from argv[1], converts HTML blocks to raw LaTeX {=latex} fences,
strips the TOML frontmatter, and writes the result to stdout for pandoc.
"""

import re
import sys


def html_to_latex(s, br=r"\newline "):
    """Strip inline HTML and convert to LaTeX equivalents.

    br: line-break string for <br> tags. Passed via lambda to re.sub so
    backslashes are NOT further processed by the regex engine.
    """
    s = re.sub(r"\n\s*", " ", s)
    s = re.sub(r"\s+", " ", s)
    # Entities
    s = s.replace("&amp;", r"\&")
    s = s.replace("&lt;", "<")
    s = s.replace("&gt;", ">")
    s = s.replace("&nbsp;", "~")
    # Unicode math characters (safe for all TeX engines)
    s = s.replace("→", r"$\rightarrow$")
    s = s.replace("×", r"$\times$")
    # Inline formatting — order matters (strong before em to avoid partial matches)
    s = re.sub(r"<strong>(.*?)</strong>", lambda m: r"\textbf{" + m.group(1) + "}", s)
    s = re.sub(r"<b>(.*?)</b>",           lambda m: r"\textbf{" + m.group(1) + "}", s)
    s = re.sub(r"<em>(.*?)</em>",         lambda m: r"\textit{" + m.group(1) + "}", s)
    s = re.sub(r"<i>(.*?)</i>",           lambda m: r"\textit{" + m.group(1) + "}", s)
    s = re.sub(r"<small>(.*?)</small>",   lambda m: r"{\small " + m.group(1) + "}", s)
    # Hyperlinks
    s = re.sub(
        r'<a\s[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        lambda m: r"\href{" + m.group(1) + "}{" + m.group(2) + "}",
        s,
    )
    # Line breaks — lambda avoids re.sub backslash processing of the br string
    s = re.sub(r"<br\s*/?>\s*", lambda _: br, s)
    # Strip remaining tags
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()


def raw_latex(latex):
    return f"\n```{{=latex}}\n{latex.strip()}\n```\n"


def convert_header_div(html):
    """Centered header div → LaTeX center block with \\ line breaks."""
    m = re.search(r"<div[^>]*>(.*?)</div>", html, re.DOTALL)
    if not m:
        return ""
    # Use \\ (two backslashes) for center-env line breaks
    content = html_to_latex(m.group(1), br="\\\\\n")
    return raw_latex(f"\\begin{{center}}\n{content}\n\\end{{center}}")


def parse_cv_table(html):
    """Convert <table class="cv-table"> to LaTeX tabularx."""
    rows = re.findall(r"<tr>(.*?)</tr>", html, re.DOTALL)
    latex_rows = []
    for i, row in enumerate(rows):
        cells = re.findall(r"<td[^>]*>(.*?)</td>", row, re.DOTALL)
        if len(cells) >= 2:
            date = html_to_latex(cells[0])       # \newline default (unused in dates)
            content = html_to_latex(cells[1])    # \newline for multi-line cells
            strut = r"\rule{0pt}{2.5ex}" if i > 0 else ""
            latex_rows.append(f"  {strut}{date} & {content} \\\\")

    # >{\raggedleft\arraybackslash}p{2.5cm} = fixed-width right-aligned date column
    col = r">{\raggedleft\arraybackslash}p{2.5cm}|X"
    lines = [
        r"\vspace{0.3em}",
        f"\\begin{{tabularx}}{{\\linewidth}}{{{col}}}",
        *latex_rows,
        r"\end{tabularx}",
        r"\vspace{-0.3em}",
    ]
    return raw_latex("\n".join(lines))


def pub_md_to_latex(s):
    """Convert markdown inline syntax to LaTeX for publication entry text.

    Handles bold, italic, escaped asterisks, bracketed links, and <br> tags.
    Must produce a complete raw LaTeX block (no pandoc processing afterwards).
    """
    # <br> → LaTeX line break (two backslashes + newline)
    s = s.replace("<br>", "\\\\\n")
    # Bracketed links: \[[text](url)\] → [\href{url}{text}]
    s = re.sub(
        r'\\\[([^\]]*)\]\(([^)]+)\)\\\]',
        lambda m: r'[\href{' + m.group(2) + '}{' + m.group(1) + '}]',
        s,
    )
    # Bold **text** — must come before italic to avoid partial match on ***
    s = re.sub(r'\*\*(.+?)\*\*', lambda m: r'\textbf{' + m.group(1) + '}', s)
    # Italic *text* — but not \* (escaped asterisk for student indicator)
    s = re.sub(r'(?<!\\)\*(.+?)\*', lambda m: r'\textit{' + m.group(1) + '}', s)
    # Escaped asterisk \* → bare * (student indicator symbol)
    s = s.replace('\\*', '*')
    return s


def wrap_publication_entries(text):
    """Convert each numbered publication entry to a raw LaTeX block.

    Outputs a single fenced {=latex} block so that \\hangindent is set inside
    the same TeX group as the paragraph text — avoiding the \\par reset that
    would occur if \\hangindent were in a separate raw block preceding a
    pandoc-processed markdown paragraph.
    """
    def replacer(m):
        content = pub_md_to_latex(m.group(0).strip())
        latex = (
            "\\begin{samepage}\n"
            "{\\hangindent=1.5em\\hangafter=1\n"
            + content
            + "\\par}\n"
            "\\end{samepage}"
        )
        return raw_latex(latex)
    # Match lines starting with a bold number like **8.**
    return re.sub(
        r'^\*\*\d+\.\*\*\s+.+$',
        replacer,
        text,
        flags=re.MULTILINE,
    )


def convert_heading(m):
    """## Section title → bold heading + horizontal rule."""
    title = m.group(1).strip()
    latex = (
        "\n\\needspace{5\\baselineskip}\n"
        "\\vspace{0.8em}\n"
        f"\\begin{{flushleft}}\\textbf{{{title}}}\\end{{flushleft}}\n"
        "\\vspace{-0.9em}\n"
        "\\noindent\\rule{\\textwidth}{0.4pt}\n"
        "\\vspace{-1.2em}\n"
    )
    return raw_latex(latex)


def process(text):
    # 1. Strip TOML frontmatter (between first and second +++ delimiters)
    text = re.sub(r"^\+\+\+\s*\n.*?\+\+\+\s*\n", "", text, flags=re.DOTALL)

    # 2. Strip HTML comments (<!-- ... -->) before any other processing so their
    #    content doesn't accidentally match headings, tables, etc.
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)

    # 2. Centered header div → \begin{center}...\end{center}
    text = re.sub(
        r"<div[^>]*text-align\s*:\s*center[^>]*>.*?</div>",
        lambda m: convert_header_div(m.group(0)),
        text,
        flags=re.DOTALL,
    )

    # 3. Remove download-PDF link paragraph
    text = re.sub(
        r"<p[^>]*>.*?Download PDF.*?</p>\s*\n?",
        "",
        text,
        flags=re.DOTALL,
    )

    # 4. cv-tables → tabularx
    text = re.sub(
        r'<table class="cv-table">.*?</table>',
        lambda m: parse_cv_table(m.group(0)),
        text,
        flags=re.DOTALL,
    )

    # 5. Standalone <small> block (publication footnote line)
    text = re.sub(
        r"^<small>(.*?)</small>\s*$",
        lambda m: raw_latex(r"{\small " + html_to_latex(m.group(1)) + "}"),
        text,
        flags=re.MULTILINE | re.DOTALL,
    )

    # 6. Horizontal rules (---) → strip; section headings add their own rules
    text = re.sub(r"^---\s*$", "", text, flags=re.MULTILINE)

    # 7. ## Section headings → bold + rule
    text = re.sub(r"^## (.+)$", convert_heading, text, flags=re.MULTILINE)

    # 8. Wrap numbered publication entries in samepage to prevent mid-entry page breaks
    text = wrap_publication_entries(text)

    return text.strip()


if __name__ == "__main__":
    with open(sys.argv[1], encoding="utf-8") as f:
        content = f.read()
    print(process(content))
