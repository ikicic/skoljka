# -*- coding: utf-8 -*-

from __future__ import print_function

from skoljka.mathcontent.converter_v1 import Converter, Tokenizer
from skoljka.mathcontent.converter_v1.basics import SKIP_COMPARISON as SKIP
from skoljka.mathcontent.converter_v1.bbcode import BBCodeException, parse_bbcode
from skoljka.mathcontent.converter_v1.latex import (
    LatexEnvironmentDiv,
    LatexEnvironmentFigure,
    LatexEnvironmentVerbatim,
    LatexValueError,
    convert_tex_length_to_html,
)
from skoljka.mathcontent.converter_v1.tokens import (
    TokenBBCode,
    TokenClosedCurly,
    TokenCommand,
    TokenComment,
    TokenError,
    TokenMath,
    TokenMultilineWhitespace,
    TokenOpenCurly,
    TokenSimpleWhitespace,
    TokenText,
    TokenWarning,
)
from skoljka.mathcontent.models import LatexElement
from skoljka.utils.testcase import SimpleTestCase


class MockFile(object):
    def __init__(self, fn):
        self.filename = fn


class MockAttachment(object):
    def __init__(self, fn):
        self.file = MockFile(fn)

    def get_url(self):
        return "/mock/" + self.file.filename

    def get_filename(self):
        return self.file.filename


class MockConverter(Converter):
    def generate_png(self, hash, format, latex):
        return LatexElement(hash=hash, format=format, text=latex, depth=0)

    def generate_latex_hash(self, format, latex):
        return "<<{}||{}>>".format(format, latex)

    def get_available_latex_elements(self, formulas):
        return {}

    def get_latex_html(self, element, force_inline):
        return ("INLINE:" if force_inline else "") + element.hash


class ConverterV1TestCase(SimpleTestCase):
    def setUp(self):
        self.attachments = [
            MockAttachment('first.png'),
            MockAttachment('second.png'),
        ]

    def assertEqualPrint(self, received, expected):
        if received != expected:
            print()
            print("Received: ", repr(unicode(received)))
            print("Expected: ", repr(unicode(expected)))
            # print("Received: ", received)
            # print("Expected: ", expected)
            self.fail("Received != Expected")

    def assertTokenization(self, input, expected_tokens, *args, **kwargs):
        tokenizer = Tokenizer(input, *args, **kwargs)
        tokens = tokenizer.tokenize()
        self.assertEqual(tokens, expected_tokens)

    def assertHTML(self, input, output, *args, **kwargs):
        self.assertHTMLLatex(input, output, None, *args, **kwargs)

    def assertLatex(self, input, output, *args, **kwargs):
        self.assertHTMLLatex(input, None, output, *args, **kwargs)

    def assertHTMLLatex(
        self, input, output_html, output_latex, converter_kwargs={}, *args, **kwargs
    ):
        tokenizer = Tokenizer(input)
        tokens = tokenizer.tokenize()
        converter = MockConverter(
            tokens, tokenizer, attachments=self.attachments, **converter_kwargs
        )
        if output_html is not None:
            self.assertEqualPrint(converter.convert_to_html(), output_html)
        if output_latex is not None:
            self.assertEqualPrint(converter.convert_to_latex(), output_latex)

    def assertHTMLLatexNoPar(self, *args, **kwargs):
        if 'converter_kwargs' not in kwargs:
            kwargs['converter_kwargs'] = {}
        kwargs['converter_kwargs']['paragraphs_disabled'] = True
        self.assertHTMLLatex(*args, **kwargs)

    def assertHTMLAutoLatex(self, input, output_html, *args, **kwargs):
        self.assertHTMLLatex(input, output_html, input, *args, **kwargs)

    def assertHTMLAutoLatexNoPar(self, input, output_html, *args, **kwargs):
        self.assertHTMLLatexNoPar(input, output_html, input, *args, **kwargs)

    def test_helper_functions(self):
        # TODO: Test other helper functions.

        # Test convert_tex_length_to_html.
        self.assertMultipleEqualOrRaise(
            convert_tex_length_to_html,
            [
                ('1em', '1em'),
                ('1.em', '1.em'),
                ('.5em', '.5em'),
                ('1.2341em', '1.2341em'),
                ('5634em', '5634em'),
                ('em', LatexValueError),
                ('1xy', LatexValueError),
                ('1xyz', LatexValueError),
                ('72.27pt', '72.0pt'),
                ('1mm', '1mm'),
                ('1cm', '1cm'),
                ('1in', '1in'),
                ('1ex', '1ex'),
                ('1em', '1em'),
                ('144bp', '2.0in'),
                ('1pc', '11.9551681pt'),
                ('1dd', '0.99626401pt'),
                ('1cc', '11.9551681pt'),
                ('1sp', '1.52017824e-05pt'),
            ],
        )

    def test_tokenization(self):
        self.assertTokenization("bla", [TokenText("bla")])
        self.assertTokenization("bla  bla", [TokenText("bla  bla")])
        self.assertTokenization("bla~bla", [TokenText("bla~bla")])
        self.assertTokenization(
            "bla\n  bla",
            [
                TokenText("bla"),
                TokenSimpleWhitespace("\n  "),
                TokenText("bla"),
            ],
        )
        self.assertTokenization(
            "bla \n \n   bla",
            [
                TokenText("bla"),
                TokenMultilineWhitespace(" \n \n   "),
                TokenText("bla"),
            ],
        )
        self.assertTokenization(
            "bla $a + b = c$ \n$$d*f+g  $$ dummy$$$$$$$$$a+b$\n  bla",
            [
                TokenText("bla"),
                TokenSimpleWhitespace(" "),
                TokenMath('$%s$', "a + b = c"),
                TokenSimpleWhitespace(" \n"),
                TokenMath('$$%s$$', "d*f+g  "),
                TokenSimpleWhitespace(" "),
                TokenText("dummy"),
                TokenMath('$$%s$$', ""),
                TokenMath('$$%s$$', ""),
                TokenMath('$%s$', "a+b"),
                TokenSimpleWhitespace("\n  "),
                TokenText("bla"),
            ],
        )
        self.assertTokenization(
            "bla \\( a+b  \\)\n\n\\[\n   c*d\n\\]\n\nbla bla",
            [
                TokenText("bla"),
                TokenSimpleWhitespace(" "),
                TokenMath(r'\(%s\)', " a+b  "),
                TokenMultilineWhitespace("\n\n"),
                TokenMath(r'\[%s\]', "\n   c*d\n"),
                TokenMultilineWhitespace("\n\n"),
                TokenText("bla bla"),
            ],
        )
        self.assertTokenization(
            "$not finished",
            [
                TokenError(SKIP, "$not finished"),
            ],
        )
        self.assertTokenization(
            "without error $before\\%after$",
            [
                TokenText("without error"),
                TokenSimpleWhitespace(" "),
                TokenMath("$%s$", "before\\%after"),
            ],
        )
        self.assertTokenization(
            "with error $before\\\\%after$\nnext",
            [
                TokenText("with error"),
                TokenSimpleWhitespace(" "),
                TokenError(SKIP, "$before\\\\%after$\nnext"),
            ],
        )
        self.assertTokenization(
            "again without error $before\\\\%after$\nnext$",
            [
                TokenText("again without error"),
                TokenSimpleWhitespace(" "),
                TokenMath("$%s$", "before\\\\%after$\nnext"),
            ],
        )
        self.assertTokenization(
            "again again without error $before\\\\\\%after$",
            [
                TokenText("again again without error"),
                TokenSimpleWhitespace(" "),
                TokenMath("$%s$", "before\\\\\\%after"),
            ],
        )

        self.assertTokenization(
            "\\\\ \\\\",
            [
                # Not sure about this one.
                TokenCommand('\\', whitespace=[" "]),
                TokenCommand('\\'),
            ],
        )
        self.assertTokenization(
            "\\textasciicircum\\textasciitilde  \\textbackslash",
            [
                TokenCommand('textasciicircum'),
                TokenCommand('textasciitilde', whitespace=["  "]),
                TokenCommand('textbackslash'),
            ],
        )
        self.assertTokenization(
            "bla\\unknownname bla",
            [
                TokenText("bla"),
                TokenError(SKIP, "\\unknownname"),
                TokenSimpleWhitespace(" "),
                TokenText("bla"),
            ],
        )
        self.assertTokenization(
            # Comment picks all the leading whitespace from the next line.
            "bla\r\n% a comment\n   blabla % another comment",
            [
                TokenText("bla"),
                TokenSimpleWhitespace("\r\n"),
                TokenComment(" a comment\n   "),
                TokenText("blabla"),
                TokenSimpleWhitespace(" "),
                TokenComment(" another comment"),
            ],
        )
        self.assertTokenization(r"\url{bla}", [TokenCommand('url', 0, ["bla"])])
        self.assertTokenization(r"\url{b%la}", [TokenCommand('url', 0, ["b%la"])])
        self.assertTokenization(r"\url{b{}%la}", [TokenCommand('url', 0, ["b{}%la"])])
        self.assertTokenization(
            r"\url  {bla}", [TokenCommand('url', 0, ["bla"], ["  "])]
        )
        self.assertTokenization(r"\url", [TokenError(SKIP, r"\url")])
        self.assertTokenization(
            r"\url bla",
            [
                TokenError(SKIP, r"\url"),
                TokenText("bla"),
            ],
        )
        self.assertTokenization(
            "\\href  {http://www.google.com} \n  {bla}",
            [
                TokenCommand(
                    'href',
                    0,
                    ["http://www.google.com", [TokenText("bla")]],
                    ["  ", " \n  "],
                ),
                TokenText("bla"),
                TokenCommand(
                    'href',
                    1,
                    ["http://www.google.com", [TokenText("bla")]],
                    ["  ", " \n  "],
                ),
            ],
        )
        self.assertTokenization(
            r"\href{http://ww%w.g{}oogle.com}{bla}",
            [
                TokenCommand(
                    'href', 0, ["http://ww%w.g{}oogle.com", [TokenText("bla")]]
                ),
                TokenText("bla"),
                TokenCommand(
                    'href', 1, ["http://ww%w.g{}oogle.com", [TokenText("bla")]]
                ),
            ],
        )
        self.assertTokenization(
            r"\href{http://ww%w.g{}oogle.com}",
            [
                TokenError(SKIP, r"\href{http://ww%w.g{}oogle.com}"),
            ],
        )
        self.assertTokenization(
            r"\href{http://ww%w.g{}oogle.com}{bl%a}",
            [
                TokenError(SKIP, r"\href{http://ww%w.g{}oogle.com}{bl%a}"),
            ],
        )
        self.assertTokenization(
            r"\emph{bla}",
            [
                TokenCommand('emph', 0, SKIP),
                TokenText("bla"),
                TokenCommand('emph', 1, SKIP),
            ],
        )
        self.assertTokenization(
            r"\textbf{bla \sout{asdf}\uline{bla bla}}",
            [
                TokenCommand('textbf', 0, SKIP),
                TokenText("bla"),
                TokenSimpleWhitespace(" "),
                TokenCommand('sout', 0, SKIP),
                TokenText("asdf"),
                TokenCommand('sout', 1, SKIP),
                TokenCommand('uline', 0, SKIP),
                TokenText("bla bla"),
                TokenCommand('uline', 1, SKIP),
                TokenCommand('textbf', 1, SKIP),
            ],
        )
        self.assertTokenization(
            r"\includegraphics[width=100pt]{image.png}",
            [
                TokenCommand('includegraphics', 0, ["width=100pt", "image.png"]),
            ],
        )
        self.assertTokenization(
            "\\begin{center}\n  some content\n\\end{center}",
            [
                TokenCommand(
                    'begin', 0, ['center', LatexEnvironmentDiv('mc-center')], ['']
                ),
                TokenSimpleWhitespace("\n  "),
                TokenText("some content"),
                TokenSimpleWhitespace("\n"),
                TokenCommand(
                    'end', 0, ['center', LatexEnvironmentDiv('mc-center')], ['']
                ),
            ],
        )
        self.assertTokenization(
            "\\begin{asdf}bla\\end{asdf}",
            [TokenMath('%s', "\\begin{asdf}bla\\end{asdf}")],
        )

        # Test empty {}.
        self.assertTokenization(
            "\\textasciicircum \n  bla",
            [
                TokenCommand('textasciicircum', whitespace=[" \n  "]),
                TokenText("bla"),
            ],
        )
        self.assertTokenization(
            "\\textasciicircumbla",
            [
                TokenError(SKIP, "\\textasciicircumbla"),
            ],
        )
        self.assertTokenization(
            "\\textasciicircum{}  bla",
            [
                TokenCommand('textasciicircum', 0),
                TokenOpenCurly(),
                TokenClosedCurly(),
                TokenSimpleWhitespace("  "),
                TokenText("bla"),
            ],
        )

        # Test environments.
        _figure = LatexEnvironmentFigure(centering=False, tag="1")
        _flushleft = LatexEnvironmentDiv('mc-flushleft')
        self.assertTokenization(
            r'\begin{figure}'
            r'\begin{flushleft}'
            r'\includegraphics{first.png}'
            r'\end{flushleft}'
            r'\caption{Some caption here.}'
            r'\label{some-label}'
            r'\end{figure}',
            [
                TokenCommand('begin', 0, ['figure', _figure]),
                TokenCommand('begin', 0, ['flushleft', _flushleft]),
                TokenCommand('includegraphics', 0, [None, 'first.png']),
                TokenCommand('end', 0, ['flushleft', _flushleft]),
                TokenCommand('caption', 0, [[TokenText("Some caption here.")], "1"]),
                TokenText("Some caption here."),
                TokenCommand('caption', 1, [[TokenText("Some caption here.")], "1"]),
                TokenCommand('label', 0, ["some-label", ""]),
                TokenCommand('end', 0, ['figure', _figure]),
            ],
        )

        _figure = LatexEnvironmentFigure(centering=True, tag="1")
        self.assertTokenization(
            r'\begin{figure}'
            r'\includegraphics{first.png}'
            r'\caption{Some caption here.}'
            r'\label{some-label}'
            r'\centering'
            r'\end{figure}',
            [
                TokenCommand('begin', 0, ['figure', _figure]),
                TokenCommand('includegraphics', 0, [None, 'first.png']),
                TokenCommand('caption', 0, [[TokenText("Some caption here.")], "1"]),
                TokenText("Some caption here."),
                TokenCommand('caption', 1, [[TokenText("Some caption here.")], "1"]),
                TokenCommand('label', 0, ["some-label", ""]),
                TokenCommand('centering', 0),
                TokenCommand('end', 0, ['figure', _figure]),
            ],
        )

        _figure = LatexEnvironmentFigure(centering=True, tag="1")
        self.assertTokenization(
            r'\begin{figure}'
            r'\includegraphics{first.png}'
            r'\label{wrong-order}'
            r'\caption{Some caption here.}'
            r'\centering'
            r'\end{figure}',
            [
                TokenCommand('begin', 0, ['figure', _figure]),
                TokenCommand('includegraphics', 0, [None, 'first.png']),
                TokenCommand('label', 0, ["wrong-order", TokenError(SKIP, "")]),
                TokenCommand('caption', 0, [[TokenText("Some caption here.")], "1"]),
                TokenText("Some caption here."),
                TokenCommand('caption', 1, [[TokenText("Some caption here.")], "1"]),
                TokenCommand('centering', 0),
                TokenCommand('end', 0, ['figure', _figure]),
            ],
        )

        self.assertTokenization(
            "asdf\\begin{verbatim}bla\\end{verbatim}ignored\nnot-ignored",
            [
                TokenText("asdf"),
                TokenCommand(
                    'begin', 0, ['verbatim', LatexEnvironmentVerbatim(), "bla"], SKIP
                ),
                TokenWarning(SKIP, "ignored"),
                TokenSimpleWhitespace('\n'),
                TokenText("not-ignored"),
            ],
        )

        # BBCode
        self.assertTokenization("[]", [TokenText("["), TokenText("]")])
        self.assertTokenization(
            "[unknown tag]", [TokenText("["), TokenText("unknown tag"), TokenText("]")]
        )
        self.assertTokenization(
            "[b]bla[/b]",
            [
                TokenBBCode('b', [('b', None)], 0, 3),
                TokenText("bla"),
                TokenBBCode('b', None, 6, 10),
            ],
        )
        self.assertTokenization(
            "[/b]bla[b bla=\"xy\\\"z\"]",
            [
                TokenBBCode('b', None, 0, 4),
                TokenText("bla"),
                TokenBBCode('b', [('b', None), ('bla', "xy\"z")], SKIP, SKIP),
            ],
        )

        self.assertTokenization(
            "[url=http://www.example.com/]title[/url]",
            [
                TokenBBCode('url', [('url', 'http://www.example.com/')], 0, SKIP),
                TokenText("title"),
                TokenBBCode('url', None, SKIP, SKIP),
            ],
        )
        self.assertTokenization(
            "[url]http://www.example.com/[/url]",
            [
                TokenBBCode('url', [('url', None)], 0, SKIP, "http://www.example.com/"),
            ],
        )

    def test_latex_commands(self):
        # Newlines are always seperated as TokenSimpleWhitespace, which then
        # is replaced with a single whitespace (for HTML that is enough).
        self.assertHTMLAutoLatexNoPar("bla", "bla")
        self.assertHTMLAutoLatexNoPar("bla~bla", "bla&nbsp;bla")
        self.assertHTMLAutoLatexNoPar("bla\nbla", "bla bla")
        self.assertHTMLAutoLatexNoPar("bla\n\nbla", "bla<br>bla")
        self.assertHTMLAutoLatexNoPar("bla  \n\n  bla", "bla<br>bla")
        self.assertHTMLAutoLatexNoPar("bla  \n \n \n\n  bla", "bla<br>bla")
        self.assertHTMLAutoLatexNoPar("bla\n\n\n\nbla", "bla<br>bla")

        self.assertHTMLAutoLatexNoPar(
            "\\textbackslash begin\\{...\\} ... \\textbackslash end\\{...\\}",
            "\\begin{...} ... \\end{...}",
        )
        self.assertHTMLAutoLatexNoPar(
            "\\textbackslash{}begin\\{...\\} ... \\textbackslash{}end\\{...\\}",
            "\\begin{...} ... \\end{...}",
        )
        self.assertHTMLAutoLatexNoPar(
            "\\textbackslash{}\\textasciicircum{}\\textasciitilde{}", "\\^~"
        )
        self.assertHTMLAutoLatexNoPar(r"\{\}\%\_\&\$\#", "{}%_&amp;$#")
        self.assertHTMLAutoLatexNoPar("\\&\"'<>", "&amp;&quot;&apos;&lt;&gt;")

        self.assertHTMLAutoLatexNoPar(
            r"a\-very\-very\-long\-word\-here",
            r"a&shy;very&shy;very&shy;long&shy;word&shy;here",
        )
        self.assertHTMLAutoLatexNoPar(r"\TeX", r"INLINE:<<%s||\TeX>>")
        self.assertHTMLAutoLatexNoPar(r"\LaTeX", r"INLINE:<<%s||\LaTeX>>")

        self.assertHTMLAutoLatexNoPar("bla\\\\  asdf", "bla<br>asdf")
        self.assertHTMLAutoLatexNoPar("\\emph{bla bla bla}", "<em>bla bla bla</em>")
        self.assertHTMLAutoLatexNoPar(
            "\\emph  {bla \\textbf \n{bla} bla}", "<em>bla <b>bla</b> bla</em>"
        )

        self.assertHTMLAutoLatexNoPar(
            "\\href{http://www.example.com/bla%40bla}{click here}",
            '<a href="http://www.example.com/bla%40bla" rel="nofollow">'
            'click here</a>',
        )
        self.assertHTMLAutoLatexNoPar(
            "\\url{http://www.example.com/}",
            '<a href="http://www.example.com/" rel="nofollow">'
            'http://www.example.com/</a>',
        )
        self.assertHTMLAutoLatexNoPar(
            "\\url{http://www.example.com/bla%40bla}",
            '<a href="http://www.example.com/bla%40bla" rel="nofollow">'
            'http://www.example.com/bla%40bla</a>',
        )

        # Note: Look at setUp for mocked attachments.
        self.assertHTMLAutoLatexNoPar(
            "\\includegraphics{first.png}",
            '<img src="/mock/first.png" alt="Attachment first.png" class="latex">',
        )

        # TODO: Check if the conversion pt->px makes any sense.
        self.assertHTMLAutoLatexNoPar(
            "\\includegraphics  [width=100pt] {first.png}",
            '<img src="/mock/first.png" alt="Attachment first.png" class="latex" width="100">',
        )
        self.assertHTMLAutoLatexNoPar(
            "\\includegraphics[width=100pt,height=200pt]{first.png}",
            '<img src="/mock/first.png" alt="Attachment first.png" class="latex" width="100" height="200">',
        )
        self.assertHTMLAutoLatexNoPar(
            "\\includegraphics[scale=0.7]{first.png}",
            '<img src="/mock/first.png" alt="Attachment first.png" class="latex" width="70%" height="70%">',
        )
        self.assertHTMLAutoLatexNoPar(
            "\\includegraphics[scale=0.7123]{first.png}",
            '<img src="/mock/first.png" alt="Attachment first.png" class="latex" width="71.23%" height="71.23%">',
        )

        self.assertHTMLAutoLatexNoPar("bla\\textasciicircum{}asdf", "bla^asdf")
        self.assertHTMLAutoLatexNoPar("bla\\textasciicircum{}asdf", "bla^asdf")
        self.assertHTMLAutoLatexNoPar("bla\\textasciitilde{}asdf", "bla~asdf")
        self.assertHTMLAutoLatexNoPar(
            "something\\textbackslash{}something", "something\\something"
        )

        # Simple containers.
        self.assertHTMLAutoLatexNoPar(
            "\\fbox{do not wrap this part}",
            '<span class="mc-fbox">do not wrap this part</span>',
        )
        self.assertHTMLAutoLatexNoPar(
            "\\mbox{do not wrap this part}",
            '<span class="mc-mbox">do not wrap this part</span>',
        )
        self.assertHTMLAutoLatexNoPar("\\textbf{bla bla bla}", "<b>bla bla bla</b>")
        self.assertHTMLAutoLatexNoPar("\\textit{bla bla bla}", "<i>bla bla bla</i>")
        self.assertHTMLAutoLatexNoPar(
            "\\texttt{bla bla bla}", "<code>bla bla bla</code>"
        )
        self.assertHTMLAutoLatexNoPar(
            "\\underline{underlined with nowrap}",
            '<span class="mc-underline">underlined with nowrap</span>',
        )
        self.assertHTMLAutoLatexNoPar(
            "asdf \\sout{bla bla} qwerty \\uline{asdf}",
            "asdf <s>bla bla</s> qwerty <u>asdf</u>",
        )

        # Begin commands.
        self.assertHTMLAutoLatexNoPar(
            "\\begin{center}\\textbf{bla}\\end{center}",
            '<div class="mc-center"><b>bla</b></div>',
        )
        self.assertHTMLAutoLatexNoPar(
            "\\begin\n{center}\\textbf  {bla}\\end \n{center}",
            '<div class="mc-center"><b>bla</b></div>',
        )
        self.assertHTMLAutoLatexNoPar(
            "\\begin{xyz}something\\end{xyz}", "<<%s||\\begin{xyz}something\\end{xyz}>>"
        )
        self.assertHTMLAutoLatexNoPar(
            "\\begin{xyz}something\\\\end{xyz}\\end{xyz}",
            "<<%s||\\begin{xyz}something\\\\end{xyz}\\end{xyz}>>",
        )
        self.assertHTMLLatexNoPar(
            "\\begin{xyz}\\textbf{sar%ma}\\end{xyz}",
            "<<ERROR>>",  # \\end is in the comment.
            "<<ERROR>>",
            converter_kwargs={'errors_mode': Converter.ERRORS_TESTING},
        )
        self.assertHTMLLatexNoPar(
            "\\begin{xyz}\\url{sar%ma}\\end{xyz}",
            "<<ERROR>>",  # SIMPLIFICATION MARK. Do not complicate with %.
            "<<ERROR>>",
            converter_kwargs={'errors_mode': Converter.ERRORS_TESTING},
        )
        self.assertHTMLAutoLatexNoPar(
            "\\begin{verbatim}\\textbf  {bla}\nasdf\\end{verbatim}",
            '<pre class="mc-verbatim">\\textbf  {bla}\nasdf</pre>',
        )
        self.assertHTMLAutoLatexNoPar(
            "\\begin{verbatim}<xss check>\\end{verbatim}",
            '<pre class="mc-verbatim">&lt;xss check&gt;</pre>',
        )
        self.assertHTMLAutoLatexNoPar(
            "\\begin{verbatim*}<xss check>  asdf\\end{verbatim*}",
            '<pre class="mc-verbatim">&lt;xss&blank;check&gt;&blank;&blank;asdf</pre>',
        )

        # Math mode.
        self.assertHTMLAutoLatexNoPar("$a+b$", "<<$%s$||a+b>>")
        self.assertHTMLAutoLatexNoPar(r"\(a+b\)", r"<<\(%s\)||a+b>>")
        self.assertHTMLAutoLatexNoPar(r"\[ a+b \]", r"<<\[%s\]|| a+b >>")
        self.assertHTMLAutoLatexNoPar("$$  a+b $$", "<<$$%s$$||  a+b >>")

        # Figures and environment testing.
        self.assertHTMLAutoLatexNoPar(
            r'\begin{figure}'
            r'\includegraphics{first.png}'
            r'\caption{Some caption here <xss check>.}'
            r'\label{some-label}'
            r'\centering'
            r'\end{figure}',
            '<div class="mc-figure mc-center">'
            '<img src="/mock/first.png" alt="Attachment first.png" class="latex">'
            '<div class="mc-caption"><span class="mc-caption-tag">Slika 1:</span> Some caption here &lt;xss check&gt;.</div>'
            '</div>',
        )
        self.assertHTMLAutoLatexNoPar(
            r'\begin{figure}'
            r'\includegraphics{first"><xss check=".png}'
            r'\end{figure}',
            '<div class="mc-figure"><<ERROR>></div>',  # Not found error at least.
            converter_kwargs={'errors_mode': Converter.ERRORS_TESTING},
        )

        # Complex example.
        self.assertHTMLAutoLatexNoPar(
            r'\begin{figure}'
            r'\begin{flushleft}'
            r'\includegraphics{first.png}'
            r'\end{flushleft}'
            r'\caption{Some caption here.}'
            r'\label{label-after-accepted}'
            r'\end{figure}'
            r''
            r'\begin{figure}'
            r'\centering'
            r'\includegraphics{second.png}'
            r'\label{label-before-ignored}'
            r'\caption{Another caption here.}'
            r'\end{figure}'
            r''
            r'First: \ref{label-after-accepted}'
            r'Second: \ref{label-before-ignored}',
            '<div class="mc-figure">'
            '<div class="mc-flushleft">'
            '<img src="/mock/first.png" alt="Attachment first.png" class="latex">'
            '</div>'
            '<div class="mc-caption"><span class="mc-caption-tag">Slika 1:</span> Some caption here.</div>'
            '</div>'
            ''
            '<div class="mc-figure mc-center">'
            '<img src="/mock/second.png" alt="Attachment second.png" class="latex">'
            '<<ERROR>>'
            '<div class="mc-caption"><span class="mc-caption-tag">Slika 2:</span> Another caption here.</div>'
            '</div>'
            ''
            'First: <<$%s$||1>>'
            'Second: <<$%s$||??>>',
            converter_kwargs={'errors_mode': Converter.ERRORS_TESTING},
        )

    # # def test_bla(self):
    # #     #self.assertHTMLAutoLatexNoPar("", "")
    # #     pass

    def test_paragraphs(self):
        self.assertHTMLAutoLatex("bla", '<p class="mc-noindent">bla')
        self.assertHTMLAutoLatex("\\textbf{bla}", '<p class="mc-noindent"><b>bla</b>')
        self.assertHTMLLatex(
            "[b]bla[/b]", '<p class="mc-noindent"><b>bla</b>', "\\textbf{bla}"
        )
        self.assertHTMLAutoLatex(
            "first  \n \n \n\n  second \n\n third",
            '<p class="mc-noindent">first'
            '<p class="mc-indent">second'
            '<p class="mc-indent">third',
        )

        # No paragraph after an $$ ... $$ equation.
        self.assertHTMLAutoLatex(
            "asdf $$a + b = c$$ hjkl",
            '<p class="mc-noindent">asdf <<$$%s$$||a + b = c>> hjkl',
        )
        # self.assertHTMLAutoLatex(
        #         "asdf\n\\begin{equation}a + b = c\\end{equation}hjkl",
        #         '<p class="mc-noindent">asdf <<$$%s$$||a + b = c>>hjkl')

        # Do or do not add first paragraph depending on the beginning content.
        self.assertHTMLAutoLatex(
            "$$first row formula should have a paragraph$$",
            '<p class="mc-noindent">'
            '<<$$%s$$||first row formula should have a paragraph>>',
        )
        self.assertHTMLAutoLatex(
            "\\begin{center}no paragraph before div\\end{center}",
            '<div class="mc-center">'
            '<p class="mc-noindent">no paragraph before div'
            '</div>',
        )
        self.assertHTMLAutoLatex("\\TeX", '<p class="mc-noindent">INLINE:<<%s||\\TeX>>')

        # Depending on the whitespace after environment, put indent or noindent.
        # (test _HTMLConverterState.last_was_block)
        self.assertHTMLAutoLatex(
            "\\begin{center}bla\\end{center}\nno indent here",
            '<div class="mc-center">'
            '<p class="mc-noindent">bla'
            '</div> '
            '<p class="mc-noindent">no indent here',
        )
        self.assertHTMLAutoLatex(
            "\\begin{center}bla\\end{center}\n\nindent here",
            '<div class="mc-center">'
            '<p class="mc-noindent">bla'
            '</div>'
            '<p class="mc-indent">indent here',
        )
        self.assertHTMLAutoLatex(
            "bla\n\n\\begin{center}bla\\end{center}\nno indent here",
            '<p class="mc-noindent">bla'
            '<div class="mc-center">'
            '<p class="mc-noindent">bla'
            '</div> '
            '<p class="mc-noindent">no indent here',
        )

        for env in ['center', 'flushleft', 'flushright']:
            # Center, flushleft and flushright should always have noindent.
            self.assertHTMLAutoLatex(
                "First\n\n"
                "Second\n"
                "\\begin{%s}Inner first\n\nInner second\\end{%s}\n\n"
                "Third\n\n"
                "Fourth" % (env, env),
                '<p class="mc-noindent">First'
                '<p class="mc-indent">Second '
                '<div class="mc-%s">'
                '<p class="mc-noindent">Inner first'
                '<p class="mc-noindent">Inner second'
                '</div>'
                '<p class="mc-indent">Third'
                '<p class="mc-indent">Fourth' % env,
            )

        # Test \parindent and \parskip.
        self.assertHTMLAutoLatex(
            "\\setlength{\\parindent}{2em}First\n\nSecond",
            '<p class="mc-noindent">First' '<p style="text-indent:2em;">Second',
        )
        self.assertHTMLAutoLatex(
            "\\setlength{\\parskip}{1.5in}First\n\nSecond",
            '<p class="mc-noindent" style="margin-top:1.5in;">First'
            '<p class="mc-indent" style="margin-top:1.5in;">Second',
        )
        self.assertHTMLAutoLatex(  # Test {...} scope.
            "{\\setlength{\\parindent}{2em}First\n\nSecond}\n\nThird",
            '<p class="mc-noindent">First'
            '<p style="text-indent:2em;">Second'
            '<p class="mc-indent">Third',
        )
        self.assertHTMLLatex(  # Test {...} scope.
            "{[par 1.5in 2em]First\n\nSecond}\n\nThird",
            '<p class="mc-noindent" style="margin-top:1.5in;">First'
            '<p style="margin-top:1.5in;text-indent:2em;">Second'
            '<p class="mc-indent">Third',
            "{"
            "\\setlength{\\parskip}{1.5in}\n"
            "\\setlength{\\parindent}{2em}\n"
            "First\n\n"
            "Second"
            "}\n\n"
            "Third",
        )
        self.assertLatex(
            "[par 12pt 13pt]",
            "\\setlength{\\parskip}{12pt}\n\\setlength{\\parindent}{13pt}\n",
        )
        self.assertLatex("[par 12adfs 13pt]", "[par 12adfs 13pt]")
        self.assertLatex(
            "[par 0 1em]",
            "\\setlength{\\parskip}{0pt}\n\\setlength{\\parindent}{1em}\n",
        )
        self.assertHTMLAutoLatex(
            "\\setlength{\\parindent}{2em}\n"
            "\\setlength{\\parskip}{3em}\n"
            "\n"
            "First paragraph\n"
            "\n"
            "Second paragraph",
            '<p class="mc-noindent" style="margin-top:3em;">First paragraph'
            '<p style="margin-top:3em;text-indent:2em;">Second paragraph',
        )

    def test_bbcode(self):
        self.assertEqual(parse_bbcode("[b]", 0), ('b', [('b', None)], 3))
        self.assertEqual(parse_bbcode("[b]bla", 0), ('b', [('b', None)], 3))
        self.assertEqual(parse_bbcode("[/b]bla", 0), ('b', None, 4))
        self.assertRaises(BBCodeException, lambda: parse_bbcode("[/b=5]", 0))
        self.assertRaises(BBCodeException, lambda: parse_bbcode("[/b asdf]", 0))
        self.assertEqual(
            parse_bbcode("[asdf=bla]x", 0), ('asdf', [('asdf', "bla")], 10)
        )
        self.assertEqual(
            parse_bbcode("[abc def=ghi]x", 0),
            ('abc', [('abc', None), ('def', "ghi")], 13),
        )
        self.assertEqual(
            parse_bbcode("[abc def=ghi asdf]x", 0),
            ('abc', [('abc', None), ('def', "ghi"), ('asdf', None)], 18),
        )
        self.assertEqual(
            parse_bbcode("[abc def='ghi \\'asdf']x", 0),
            ('abc', [('abc', None), ('def', "ghi 'asdf")], 22),
        )
        self.assertRaises(
            BBCodeException, lambda: parse_bbcode("[abc def='ghi \\'as\\\\'df']x", 0)
        )
        self.assertEqual(
            parse_bbcode("[abc def=\"ghi a\\'\\\"sdf\"]x", 0),
            ('abc', [('abc', None), ('def', "ghi a\\'\"sdf")], 24),
        )
        self.assertEqual(
            parse_bbcode("[abc def=\"][[]][\"]x", 0),
            ('abc', [('abc', None), ('def', "][[]][")], 18),
        )

        self.assertHTMLLatexNoPar("bla [b bla", "bla [b bla", "bla [b bla")
        self.assertHTMLLatexNoPar("bla [b bla]", "bla [b bla]", "bla [b bla]")
        self.assertHTMLLatexNoPar("[b]bla[/b]", "<b>bla</b>", "\\textbf{bla}")
        self.assertHTMLLatexNoPar("[nobb][b]bla[/b][/nobb]", "[b]bla[/b]", "[b]bla[/b]")
        self.assertHTMLLatexNoPar(
            "[nobb][b]bla[/b]",  # special tag, no need for [/nobb]
            "[b]bla[/b]",
            "[b]bla[/b]",
        )
        self.assertHTMLLatexNoPar(
            "[/nobb][b]bla[/b]", "[/nobb]<b>bla</b>", "[/nobb]\\textbf{bla}"
        )
        self.assertHTMLLatexNoPar("[b]bla[/bb]", "[b]bla[/bb]", "[b]bla[/bb]")
        self.assertHTMLLatexNoPar(
            "Is this [b]example [i]working[/i][/b]?",
            "Is this <b>example <i>working</i></b>?",
            "Is this \\textbf{example \\textit{working}}?",
        )
        self.assertHTMLLatexNoPar(
            "A [b]complex [i]example[/i] [s]bla[u]asdf[/u][/s][/b]",
            "A <b>complex <i>example</i> <s>bla<u>asdf</u></s></b>",
            "A \\textbf{complex \\textit{example} \\sout{bla\\uline{asdf}}}",
        )
        self.assertHTMLLatexNoPar(
            "[center]This is centered[/center]",
            '<div class="mc-center">This is centered</div>',
            "\\begin{center}This is centered\\end{center}",
        )
        self.assertHTMLLatexNoPar(
            "[pre]This is pre\n    This is pre[/pre]",
            '<pre class="mc-verbatim">This is pre\n    This is pre</pre>',
            "\\begin{verbatim}This is pre\n    This is pre\\end{verbatim}\n",
        )
        self.assertHTMLLatexNoPar(
            "[pre]<xss check>[/pre]",
            '<pre class="mc-verbatim">&lt;xss check&gt;</pre>',
            "\\begin{verbatim}<xss check>\\end{verbatim}\n",
        )
        self.assertHTMLLatexNoPar(
            "The variable [code]x[/code].",
            "The variable <code>x</code>.",
            "The variable \\texttt{x}.",
        )
        self.assertHTMLLatexNoPar(
            "[hide]something[/hide]",
            '<div><a href="#" class="mc-hide-link">+/-</a>'
            '<div class="mc-hide-content" style="display:none;">'
            'something'
            '</div></div>',
            "{\\color{gray}something}",
        )
        self.assertHTMLLatexNoPar(
            "[hide=Bla]something[/hide]",
            '<div><a href="#" class="mc-hide-link">Bla</a>'
            '<div class="mc-hide-content" style="display:none;">'
            'something'
            '</div></div>',
            "{\\color{gray}Bla: something}",
        )
        self.assertHTMLLatexNoPar(
            "[hide=\"Click me\"]something[/hide]",
            '<div><a href="#" class="mc-hide-link">Click me</a>'
            '<div class="mc-hide-content" style="display:none;">'
            'something'
            '</div></div>',
            "{\\color{gray}Click me: something}",
        )
        self.assertHTMLLatexNoPar(  # Error.
            "[hide=Click me]something[/hide]",
            "[hide=Click me]something[/hide]",
            "[hide=Click me]something[/hide]",
        )
        self.assertHTMLLatexNoPar(
            "[img attachment=1]",
            '<img src="/mock/first.png" alt="Attachment #1" class="latex">',
            "\\includegraphics{first.png}",
        )
        self.assertHTMLLatexNoPar(
            "[img attachment=1 width=200px]",
            '<img src="/mock/first.png" alt="Attachment #1" class="latex" width="200">',
            "\\includegraphics[width=200pt]{first.png}",
        )
        self.assertHTMLLatexNoPar(
            "[img attachment=1 height=300px]",
            '<img src="/mock/first.png" alt="Attachment #1" class="latex" height="300">',
            "\\includegraphics[height=300pt]{first.png}",
        )
        self.assertHTMLLatexNoPar(
            "[img attachment=1 scale=0.6]",
            '<img src="/mock/first.png" alt="Attachment #1" class="latex" width="60%" height="60%">',
            "\\includegraphics[scale=0.6]{first.png}",
        )
        self.assertHTMLLatexNoPar(
            "[quote]bla bla[/quote]", '<div class="mc-quote">bla bla</div>', "bla bla"
        )
        #     self.assertHTMLLatexNoPar(
        #             "[ref=5 task=123](click here)[/ref]",
        #             r'<<$%s$||5>><a href="http://mock.com/task/123/ref/" rel="nofollow">(click here)</a>',
        #             r"$5$\href{http://mock.com/task/123/ref/}{(click here)}",
        #             converter_mock=ConverterMock)
        #     self.assertHTMLLatexNoPar(
        #             "[ref=5 task=123 page=3](click here)[/ref]",
        #             r'<<$%s$||5>><a href="http://mock.com/task/123/ref/?page=3" rel="nofollow">(click here)</a>',
        #             r"$5$\href{http://mock.com/task/123/ref/?page=3}{(click here)}",
        #             converter_mock=ConverterMock)
        self.assertHTMLLatexNoPar(
            "[url]http://example.com/[/url]",
            '<a href="http://example.com/" rel="nofollow">http://example.com/</a>',
            "\\url{http://example.com/}",
        )
        self.assertHTMLLatexNoPar(
            "[url=http://example.com/]click here[/url]",
            '<a href="http://example.com/" rel="nofollow">click here</a>',
            "\\href{http://example.com/}{click here}",
        )

    def test_bbcode_lang(self):
        self.assertHTMLLatexNoPar(
            "[lang=en]asdf[/lang]", '<div class="lang lang-en">asdf</div>', "{asdf}"
        )
        self.assertHTMLLatexNoPar(
            "[lang=hr]asdf[/lang]", '<div class="lang lang-hr">asdf</div>', "{asdf}"
        )

    def test_latex_formula(self):  # Test $ ... $ etc.
        self.assertHTMLLatexNoPar("$bla$", "<<$%s$||bla>>", "$bla$")
        self.assertHTMLLatexNoPar(r"\[bla\]", r"<<\[%s\]||bla>>", r"\[bla\]")
        self.assertHTMLLatexNoPar("$$$bla$$$", "<<%s||bla>>", "bla")
        self.assertHTMLLatexNoPar(
            "bla $$$something $a + b = c$ bla $$d + e = f$$ $$$ bla",
            "bla <<%s||something $a + b = c$ bla $$d + e = f$$ >> bla",
            "bla something $a + b = c$ bla $$d + e = f$$  bla",
        )
        self.assertHTMLLatexNoPar(r"\(bla\)", r"<<\(%s\)||bla>>", r"\(bla\)")
        self.assertHTMLLatexNoPar(r"\[bla\]", r"<<\[%s\]||bla>>", r"\[bla\]")
        self.assertHTMLLatexNoPar(
            "$$ asdf % commented out $$",
            "<<ERROR>>",
            "<<ERROR>>",
            converter_kwargs={'errors_mode': Converter.ERRORS_TESTING},
        )
        self.assertHTMLAutoLatexNoPar(
            "$$ asdf % commented out $$\n$$", "<<$$%s$$|| asdf % commented out $$\n>>"
        )

    # def test_labels(self):
    #     """Test \\label and \\ref."""
    #     self.assertHTMLAutoLatexNoPar(
    #             r"\begin{equation}\label{first}x = y + z\end{equation}" \
    #             r"ref to equation \ref{first}" \
    #             r"\begin{equation}\label{second}a = b + c\end{equation}" \
    #             r"ref to equation \ref{second}",
    #             r'<div class="mc-center"><<%s||\begin{equation}\tag{1}\label{first}x = y + z\end{equation}>></div>' \
    #             r'ref to equation <<$%s$||1>>' \
    #             r'<div class="mc-center"><<%s||\begin{equation}\tag{2}\label{second}a = b + c\end{equation}>></div>' \
    #             r'ref to equation <<$%s$||2>>',
    #             converter_mock=ConverterMock)
