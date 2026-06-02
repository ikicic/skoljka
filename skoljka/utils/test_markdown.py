from unittest import TestCase

from skoljka.utils.markdown import compile_markdown, render_latex


class CompileMarkdownTest(TestCase):
    def _html(self, source: str) -> str:
        html, _ = compile_markdown(source)
        return html

    def _text(self, source: str) -> str:
        _, text = compile_markdown(source)
        return text

    def assertKaTeX(self, html: str, tex: str):
        self.assertIn('class="katex"', html)
        self.assertIn(f'<annotation encoding="application/x-tex">{tex}</annotation>', html)

    # --- Basic Markdown ---

    def test_plain_text(self):
        self.assertEqual(self._html("hello"), "<p>hello</p>\n")

    def test_bold(self):
        self.assertEqual(self._html("**bold**"), "<p><strong>bold</strong></p>\n")

    def test_italic(self):
        self.assertEqual(self._html("*italic*"), "<p><em>italic</em></p>\n")

    def test_paragraph_break(self):
        html = self._html("a\n\nb")
        self.assertIn("<p>a</p>", html)
        self.assertIn("<p>b</p>", html)

    def test_image_width_attribute(self):
        html = self._html("![figure](attachment:figure.png){width=50%}")
        self.assertIn('src="attachment:figure.png"', html)
        self.assertIn('alt="figure"', html)
        self.assertIn('style="width: 50%;"', html)

    # --- Text-mode LaTeX compatibility commands ---

    def test_textbf_renders_strong(self):
        html = self._html(r"\textbf{bold}")
        self.assertIn("<strong>bold</strong>", html)

    def test_emph_renders_emphasis(self):
        html = self._html(r"\emph{important}")
        self.assertIn("<em>important</em>", html)

    def test_textit_renders_emphasis(self):
        html = self._html(r"\textit{italic}")
        self.assertIn("<em>italic</em>", html)

    def test_sout_renders_strikethrough(self):
        html = self._html(r"\sout{deleted}")
        self.assertIn("<s>deleted</s>", html)

    def test_uline_and_underline_render_underline(self):
        self.assertIn("<u>under</u>", self._html(r"\uline{under}"))
        self.assertIn("<u>under</u>", self._html(r"\underline{under}"))

    def test_texttt_renders_monospace(self):
        html = self._html(r"\texttt{code}")
        self.assertIn("<code>code</code>", html)

    def test_fbox_and_mbox_render_nowrap_spans(self):
        self.assertIn('<span class="latex-fbox">boxed text</span>', self._html(r"\fbox{boxed text}"))
        self.assertIn('<span class="latex-mbox">one two</span>', self._html(r"\mbox{one two}"))

    def test_double_backslash_renders_line_break(self):
        html = self._html(r"first\\second")
        self.assertIn("first<br>second", html)

    def test_url_renders_link(self):
        html = self._html(r"\url{https://example.test/a?x=1\&y=2}")
        self.assertIn('<a href="https://example.test/a?x=1&amp;y=2">https://example.test/a?x=1&amp;y=2</a>', html)

    def test_href_renders_link_with_label(self):
        html = self._html(r"\href{https://example.test}{\textbf{Example}}")
        self.assertIn('<a href="https://example.test"><strong>Example</strong></a>', html)

    def test_href_missing_second_argument_renders_error(self):
        html = self._html(r"\href{https://example.test} missing")
        self.assertIn('class="render-error"', html)
        self.assertIn("Expected second", html)

    def test_text_symbol_commands_render_symbols(self):
        html = self._html(r"\textasciicircum \textasciitilde \textbackslash")
        self.assertIn("^", html)
        self.assertIn("~", html)
        self.assertIn("&#92;", html)

    def test_text_symbol_commands_allow_empty_separator_group(self):
        self.assertIn("~foo", self._html(r"\textasciitilde{}foo"))
        self.assertIn("^foo", self._html(r"\textasciicircum{}foo"))
        self.assertIn("&#92;foo", self._html(r"\textbackslash{}foo"))

    def test_text_symbol_commands_do_not_consume_non_empty_group(self):
        self.assertIn("~{foo}", self._html(r"\textasciitilde{foo}"))

    def test_latex_escaped_special_characters_render_literals(self):
        html = self._html(r"\{ \} \% \_ \& \$ \#")
        self.assertIn("{ } % &#95; &amp; $ &#35;", html)

    def test_latex_soft_hyphen_renders_entity(self):
        html = self._html(r"extra\-ordinary")
        self.assertIn("extra&shy;ordinary", html)

    def test_text_commands_can_be_nested(self):
        html = self._html(r"\textbf{outer \emph{inner}}")
        self.assertIn("<strong>outer <em>inner</em></strong>", html)

    def test_text_command_content_can_contain_markdown(self):
        html = self._html(r"\textbf{**already bold** and _italic_}")
        self.assertIn("<strong><strong>already bold</strong> and <em>italic</em></strong>", html)

    def test_text_commands_ignore_math_context(self):
        html = self._html(r"$\textbf{x}$ and \textbf{text}")
        self.assertIn('<annotation encoding="application/x-tex">\\textbf{x}</annotation>', html)
        self.assertIn("<strong>text</strong>", html)

    def test_broken_text_command_renders_error(self):
        html = self._html(r"\textbf{unfinished")
        self.assertIn('class="render-error"', html)
        self.assertIn(r"Unclosed \textbf command", html)

    def test_known_text_command_without_brace_renders_error(self):
        html = self._html(r"This is \textbf wrong.")
        self.assertIn('class="render-error"', html)
        self.assertIn(r"\textbf", html)
        self.assertIn("wrong.", html)

    def test_known_text_command_at_end_renders_error(self):
        html = self._html(r"This is \emph")
        self.assertIn('class="render-error"', html)
        self.assertIn(r"\emph", html)

    def test_known_text_command_with_wrong_delimiter_renders_error(self):
        html = self._html(r"\textit[wrong]")
        self.assertIn('class="render-error"', html)
        self.assertIn(r"\textit", html)
        self.assertIn("[wrong]", html)

    def test_broken_nested_text_command_renders_error(self):
        html = self._html(r"\textbf{outer \emph{unfinished}")
        self.assertIn('class="render-error"', html)
        self.assertIn(r"Unclosed \textbf command", html)

    def test_unknown_latex_command_is_left_alone(self):
        html = self._html(r"\foo{bar}")
        self.assertIn(r"\foo{bar}", html)

    # --- HTML safety ---

    def test_raw_html_is_escaped(self):
        html = self._html('<script>alert("x")</script>')
        self.assertNotIn("<script", html)
        self.assertNotIn("</script>", html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&quot;x&quot;", html)

    def test_raw_html_inside_text_command_is_escaped(self):
        html = self._html(r'\textbf{<img src=x onerror="alert(1)">}')
        self.assertIn("<strong>", html)
        self.assertNotIn("<img", html)
        self.assertIn("&lt;img src=x onerror=&quot;alert(1)&quot;&gt;", html)

    def test_raw_html_inside_href_label_is_escaped(self):
        html = self._html(r'\href{https://example.test}{<span onclick="alert(1)">label</span>}')
        self.assertIn('<a href="https://example.test">', html)
        self.assertNotIn("<span", html)
        self.assertIn("&lt;span onclick=&quot;alert(1)&quot;&gt;label&lt;/span&gt;", html)

    def test_broken_command_with_raw_html_is_escaped(self):
        html = self._html(r'\textbf{<img src=x onerror="alert(1)"')
        self.assertIn('class="render-error"', html)
        self.assertNotIn("<img", html)
        self.assertNotIn("onerror=", html)
        self.assertIn("&#60;&#105;&#109;&#103;", html)

    def test_markdown_javascript_link_does_not_render_href(self):
        html = self._html("[label](javascript:alert(1))")
        self.assertNotIn("<a ", html)
        self.assertNotIn("javascript:", html)
        self.assertIn("label", html)

    def test_latex_javascript_link_does_not_render_href(self):
        html = self._html(r"\href{javascript:alert(1)}{label}")
        self.assertNotIn("<a ", html)
        self.assertNotIn("javascript:", html)
        self.assertIn("label", html)

    # --- Inline math ---

    def test_inline_math_rendered(self):
        self.assertKaTeX(self._html("$x^2$"), "x^2")

    def test_inline_math_in_text(self):
        html = self._html("Let $x$ be a variable.")
        self.assertKaTeX(html, "x")
        self.assertIn("Let", html)

    def test_multiple_inline_math(self):
        html = self._html("$a$ and $b$")
        self.assertKaTeX(html, "a")
        self.assertIn('<annotation encoding="application/x-tex">b</annotation>', html)

    # --- Display math ---

    def test_display_math_rendered(self):
        html = self._html("$$x^2 + y^2$$")
        self.assertIn('class="katex-display"', html)
        self.assertIn("<annotation encoding=\"application/x-tex\">x^2 + y^2</annotation>", html)

    def test_display_math_multiline(self):
        html = self._html("$$\na + b\n$$")
        self.assertIn('class="katex-display"', html)
        self.assertIn('<annotation encoding="application/x-tex">a + b</annotation>', html)

    # --- HTML escaping inside math ---

    def test_inline_math_less_than(self):
        html = self._html("$a < b$")
        self.assertKaTeX(html, "a &lt; b")
        self.assertNotIn("<b", html.replace("<p>", ""))

    def test_inline_math_greater_than(self):
        html = self._html("$a > b$")
        self.assertKaTeX(html, "a &gt; b")

    def test_inline_math_ampersand(self):
        html = self._html("$a & b$")
        self.assertIn('class="katex-error"', html)
        self.assertIn("a &amp; b", html)

    def test_display_math_less_than(self):
        html = self._html("$$a < b$$")
        self.assertIn('class="katex-display"', html)
        self.assertIn('<annotation encoding="application/x-tex">a &lt; b</annotation>', html)

    def test_display_math_ampersand(self):
        html = self._html("$$a & b$$")
        self.assertIn('class="katex-error"', html)
        self.assertIn("a &amp; b", html)

    def test_math_no_unnecessary_escaping(self):
        """Normal math without HTML-special chars should be unchanged."""
        html = self._html("$x^2 + y^2 = z^2$")
        self.assertKaTeX(html, "x^2 + y^2 = z^2")

    # --- Math protection from Markdown ---

    def test_underscores_in_math_not_italic(self):
        html = self._html("$a_1 + b_2$")
        self.assertNotIn("<em>", html)
        self.assertKaTeX(html, "a_1 + b_2")

    def test_stars_in_math_not_bold(self):
        html = self._html("$a * b * c$")
        self.assertNotIn("<strong>", html)
        self.assertNotIn("<em>", html)

    # --- Mixed content ---

    def test_markdown_and_math_together(self):
        html = self._html("**Bold** and $x^2$")
        self.assertIn("<strong>Bold</strong>", html)
        self.assertKaTeX(html, "x^2")

    def test_markdown_and_math_with_escaping(self):
        html = self._html("If $a < b$ then **yes**.")
        self.assertKaTeX(html, "a &lt; b")
        self.assertIn("<strong>yes</strong>", html)

    # --- Search text ---

    def test_search_text_strips_html(self):
        text = self._text("**bold** text")
        self.assertEqual(text, "bold text")

    def test_search_text_preserves_math(self):
        text = self._text("Let $x^2$ be given.")
        self.assertIn("$x^2$", text)

    def test_search_text_unescapes_math(self):
        text = self._text("$a < b$")
        self.assertEqual(text, "$a < b$")

    def test_search_text_collapses_whitespace(self):
        text = self._text("a\n\nb")
        self.assertEqual(text, "a b")

    def test_search_text_strips_text_commands(self):
        text = self._text(r"\textbf{Bold \emph{inside}} text")
        self.assertEqual(text, "Bold inside text")

    def test_search_text_keeps_broken_text_command_readable(self):
        text = self._text(r"\textbf{unfinished")
        self.assertEqual(text, r"\textbf{unfinished")

    def test_search_text_keeps_known_text_command_without_brace_readable(self):
        text = self._text(r"This is \textbf wrong.")
        self.assertEqual(text, r"This is \textbf wrong.")

    def test_search_text_for_latex_text_extensions(self):
        text = self._text(
            r"\sout{old} \uline{under} \texttt{mono} first\\second "
            r"\url{https://example.test} \href{https://example.test}{Example} "
            r"\textasciicircum\textasciitilde\textbackslash \#\_\&\$"
        )
        self.assertEqual(
            text,
            "old under mono first second https://example.test Example ^~\\ #_&$",
        )

    # --- LaTeX list environments ---

    def test_itemize_environment_renders_unordered_list(self):
        html = self._html(
            "\\begin{itemize}\n"
            "\\item First item\n"
            "\\item Second item\n"
            "\\end{itemize}"
        )

        self.assertIn("<ul>", html)
        self.assertIn("<li><p>First item</p>", html)
        self.assertIn("<li><p>Second item</p>", html)
        self.assertIn("</ul>", html)

    def test_enumerate_environment_renders_ordered_list(self):
        html = self._html(
            "\\begin{enumerate}\n"
            "\\item First item\n"
            "\\item Second item\n"
            "\\end{enumerate}"
        )

        self.assertIn("<ol>", html)
        self.assertIn("<li><p>First item</p>", html)
        self.assertIn("<li><p>Second item</p>", html)
        self.assertIn("</ol>", html)

    def test_list_items_support_markdown_text_commands_and_math(self):
        html = self._html(
            "\\begin{itemize}\n"
            "\\item **Bold** and \\emph{emph} with $x^2$\n"
            "\\end{itemize}"
        )

        self.assertIn("<strong>Bold</strong>", html)
        self.assertIn("<em>emph</em>", html)
        self.assertKaTeX(html, "x^2")

    def test_list_items_support_optional_labels(self):
        html = self._html(
            "\\begin{itemize}\n"
            "\\item[A)] First case\n"
            "\\item[B)] Second case\n"
            "\\end{itemize}"
        )

        self.assertIn('<li class="latex-labeled-item"><p><span class="latex-item-label">A)</span> First case</p>', html)
        self.assertIn('<li class="latex-labeled-item"><p><span class="latex-item-label">B)</span> Second case</p>', html)

    def test_list_item_labels_support_markdown_text_commands_and_math(self):
        html = self._html(
            "\\begin{enumerate}\n"
            "\\item[\\textbf{Case} $i$] Body\n"
            "\\end{enumerate}"
        )

        self.assertIn('<p><span class="latex-item-label"><strong>Case</strong>', html)
        self.assertKaTeX(html, "i")
        self.assertIn(" Body</p>", html)

    def test_latex_lists_can_be_nested(self):
        html = self._html(
            "\\begin{itemize}\n"
            "\\item Outer\n"
            "\\begin{enumerate}\n"
            "\\item Inner one\n"
            "\\item Inner two\n"
            "\\end{enumerate}\n"
            "\\item After\n"
            "\\end{itemize}"
        )

        self.assertIn("<ul>", html)
        self.assertIn("<ol>", html)
        self.assertIn("Inner one", html)
        self.assertIn("Inner two", html)
        self.assertIn("After", html)

    def test_item_inside_math_is_not_parsed_as_list_item(self):
        html = self._html(
            "\\begin{itemize}\n"
            "\\item Text $\\item x$\n"
            "\\end{itemize}"
        )

        self.assertEqual(html.count("<li>"), 1)
        self.assertIn('<annotation encoding="application/x-tex">\\item x</annotation>', html)

    def test_item_label_can_contain_balanced_brackets(self):
        html = self._html(
            "\\begin{itemize}\n"
            "\\item[A[1]] Nested bracket label\n"
            "\\end{itemize}"
        )

        self.assertIn('<span class="latex-item-label">A[1]</span>', html)
        self.assertIn("Nested bracket label", html)

    def test_item_label_can_contain_bracket_inside_text_command(self):
        html = self._html(
            "\\begin{itemize}\n"
            "\\item[\\textbf{A]}] Braced bracket label\n"
            "\\end{itemize}"
        )

        self.assertIn('<span class="latex-item-label"><strong>A]</strong></span>', html)
        self.assertIn("Braced bracket label", html)

    def test_mixed_labeled_and_unlabeled_items_keep_distinct_classes(self):
        html = self._html(
            "\\begin{itemize}\n"
            "\\item Plain item\n"
            "\\item[A)] Labeled item\n"
            "\\end{itemize}"
        )

        self.assertIn("<li><p>Plain item</p>", html)
        self.assertIn('<li class="latex-labeled-item"><p><span class="latex-item-label">A)</span> Labeled item</p>', html)

    def test_list_environment_contributes_to_search_text(self):
        text = self._text(
            "\\begin{itemize}\n"
            "\\item \\textbf{First}\n"
            "\\item Second $x^2$\n"
            "\\end{itemize}"
        )

        self.assertEqual(text, "First Second $x^2$")

    def test_list_item_labels_contribute_to_search_text(self):
        text = self._text(
            "\\begin{itemize}\n"
            "\\item[A)] First\n"
            "\\item[$i$] Second\n"
            "\\end{itemize}"
        )

        self.assertEqual(text, "A) First $i$ Second")

    def test_unclosed_list_environment_renders_error(self):
        html = self._html("\\begin{itemize}\n\\item Missing end")

        self.assertIn('class="render-error"', html)
        self.assertIn("Unclosed itemize environment", html)


class RenderLatexTest(TestCase):
    def _latex(self, source: str, **kwargs):
        return render_latex(source, **kwargs)

    def test_plain_text_escapes_latex_special_characters(self):
        result = self._latex(r"100% of a_b & c#d {x} ~ ^ \ end")

        self.assertEqual(
            result.body,
            r"100\% of a\_b \& c\#d \{x\} \textasciitilde{} \textasciicircum{} \textbackslash{} end",
        )

    def test_markdown_renders_normalized_latex(self):
        result = self._latex("**Bold** and *italic*")

        self.assertEqual(result.body, r"\textbf{Bold} and \emph{italic}")

    def test_math_is_preserved(self):
        result = self._latex("Let $a < b$.\n\n$$x^2 + y^2$$")

        self.assertIn(r"$a < b$", result.body)
        self.assertIn("\\[\nx^2 + y^2\n\\]", result.body)

    def test_text_commands_render_latex(self):
        result = self._latex(
            r"\textbf{bold} \emph{em} \textit{it} \sout{old} "
            r"\uline{under} \underline{also} \texttt{mono} \fbox{box} \mbox{no wrap}"
        )

        self.assertIn(r"\textbf{bold}", result.body)
        self.assertIn(r"\emph{em}", result.body)
        self.assertIn(r"\emph{it}", result.body)
        self.assertIn(r"\sout{old}", result.body)
        self.assertIn(r"\uline{under}", result.body)
        self.assertIn(r"\uline{also}", result.body)
        self.assertIn(r"\texttt{mono}", result.body)
        self.assertIn(r"\fbox{\mbox{box}}", result.body)
        self.assertIn(r"\mbox{no wrap}", result.body)
        self.assertIn("ulem", result.packages)

    def test_text_command_content_can_contain_markdown(self):
        result = self._latex(r"\textbf{**already bold** and _italic_}")

        self.assertEqual(result.body, r"\textbf{\textbf{already bold} and \emph{italic}}")

    def test_links_render_latex_and_request_hyperref(self):
        result = self._latex(r"\url{https://example.test/a?x=1\&y=2} \href{https://example.test}{\textbf{Example}}")

        self.assertIn(r"\url{https://example.test/a?x=1&y=2}", result.body)
        self.assertIn(r"\href{https://example.test}{\textbf{Example}}", result.body)
        self.assertIn("hyperref", result.packages)

    def test_unsafe_latex_link_does_not_render_href(self):
        result = self._latex(r"\href{javascript:alert(1)}{label}")

        self.assertEqual(result.body, "label")
        self.assertNotIn("hyperref", result.packages)
        self.assertNotIn(r"\href", result.body)

    def test_markdown_javascript_link_does_not_render_href(self):
        result = self._latex("[label](javascript:alert(1))")

        self.assertEqual(result.body, "label")
        self.assertNotIn(r"\href", result.body)
        self.assertNotIn("javascript:", result.body)

    def test_raw_html_is_escaped_for_latex(self):
        result = self._latex('<script>alert("x")</script>')

        self.assertNotIn("<script>", result.body)
        self.assertIn(r"\textless{}", result.body)

    def test_raw_latex_injection_is_escaped(self):
        result = self._latex(r"\input{secret} \write18{rm -rf /}")

        self.assertIn(r"\textbackslash{}input\{secret\}", result.body)
        self.assertIn(r"\textbackslash{}write18\{rm -rf /\}", result.body)

    def test_broken_known_command_reports_error_without_raw_latex(self):
        result = self._latex(r"\textbf{<img src=x onerror=""alert(1)""")

        self.assertEqual(len(result.errors), 1)
        self.assertIn("xcolor", result.packages)
        self.assertNotIn("<img", result.body)
        self.assertIn(r"\textcolor{red}", result.body)

    def test_attachment_image_uses_latex_path(self):
        result = self._latex(
            "![figure](attachment:figure.png){width=50%}",
            attachment_paths={"figure.png": "attachments/figure.png"},
        )

        self.assertEqual(result.body, r"\includegraphics[width=0.5\linewidth]{\detokenize{attachments/figure.png}}")
        self.assertIn("graphicx", result.packages)

    def test_attachment_image_path_does_not_allow_latex_injection(self):
        result = self._latex(
            "![figure](attachment:figure.png)",
            attachment_paths={"figure.png": r"attachments/a_%#\input{secret}.png"},
        )

        self.assertEqual(
            result.body,
            r"\includegraphics{\detokenize{attachments/a_%#/inputsecret.png}}",
        )

    def test_itemize_environment_exports_as_latex_list(self):
        result = self._latex(
            "\\begin{itemize}\n"
            "\\item First item\n"
            "\\item Second with \\textbf{bold}\n"
            "\\end{itemize}"
        )

        self.assertEqual(
            result.body,
            "\\begin{itemize}\n"
            "\\item First item\n"
            "\\item Second with \\textbf{bold}\n"
            "\\end{itemize}",
        )

    def test_optional_item_labels_export_as_latex(self):
        result = self._latex(
            "\\begin{itemize}\n"
            "\\item[A)] First item\n"
            "\\item[\\textbf{B}] Second item\n"
            "\\end{itemize}"
        )

        self.assertEqual(
            result.body,
            "\\begin{itemize}\n"
            "\\item[A)] First item\n"
            "\\item[\\textbf{B}] Second item\n"
            "\\end{itemize}",
        )

    def test_optional_item_label_with_bracket_in_text_command_exports_as_latex(self):
        result = self._latex(
            "\\begin{itemize}\n"
            "\\item[\\textbf{A]}] First item\n"
            "\\end{itemize}"
        )

        self.assertEqual(
            result.body,
            "\\begin{itemize}\n"
            "\\item[\\textbf{A]}] First item\n"
            "\\end{itemize}",
        )

    def test_math_item_label_exports_as_latex(self):
        result = self._latex(
            "\\begin{enumerate}\n"
            "\\item[$i$] Indexed item\n"
            "\\end{enumerate}"
        )

        self.assertEqual(
            result.body,
            "\\begin{enumerate}\n"
            "\\item[$i$] Indexed item\n"
            "\\end{enumerate}",
        )

    def test_nested_enumerate_environment_exports_as_latex_list(self):
        result = self._latex(
            "\\begin{itemize}\n"
            "\\item Outer\n"
            "\\begin{enumerate}\n"
            "\\item[(i)] Inner\n"
            "\\end{enumerate}\n"
            "\\end{itemize}"
        )

        self.assertIn("\\begin{itemize}", result.body)
        self.assertIn("\\begin{enumerate}", result.body)
        self.assertIn("\\item[(i)] Inner", result.body)
        self.assertIn("\\end{enumerate}", result.body)
        self.assertIn("\\end{itemize}", result.body)

    def test_unclosed_optional_item_label_reports_error(self):
        result = self._latex("\\begin{itemize}\n\\item[A Missing end\n\\end{itemize}")

        self.assertEqual(len(result.errors), 1)
        self.assertIn("Unclosed optional \\item label", result.errors[0]["message"])

    def test_unclosed_list_environment_exports_error(self):
        result = self._latex("\\begin{itemize}\n\\item Missing end")

        self.assertEqual(len(result.errors), 1)
        self.assertIn("Unclosed itemize environment", result.errors[0]["message"])
        self.assertIn("xcolor", result.packages)
        self.assertIn("\\textcolor{red}", result.body)
