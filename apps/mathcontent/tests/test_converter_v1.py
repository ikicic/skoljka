# -*- coding: utf-8 -*-

from django.test import TestCase

from mathcontent.converter_v1 import Tokenizer, Converter
from mathcontent.converter_v1 import SKIP_COMPARISON as SKIP
from mathcontent.converter_v1 import parse_bbcode, BBCodeException
from mathcontent.converter_v1 import TokenText, TokenCommand, \
        TokenMultilineWhitespace, TokenSimpleWhitespace, TokenMath, \
        TokenError, TokenComment, TokenOpenCurly, TokenClosedCurly, \
        TokenBBCode

from mathcontent.converter_v1 import LatexEnvironmentDiv, LatexEnvironmentFigure
from mathcontent.models import TYPE_HTML, TYPE_LATEX, LatexElement


# MOCK_URL_PREFIX = "http://mock.com/"
#
# class ConverterMock(Converter):
#     def get_latex_picture(self, format, latex):
#         return "<<{}||{}>>".format(format, latex)

def _mock__attachment(filename):
    class File(object):
        def __init__(self, fn):
            self.filename = fn

    class Attachment(object):
        def __init__(self, fn):
            self.file = File(fn)

        def get_url(self):
            return "/mock/" + self.file.filename

        def get_filename(self):
            return self.file.filename

    return Attachment(filename)


def _mock__generate_png(hash, format, latex):
    return LatexElement(hash=hash, format=format, text=latex, depth=0)

def _mock__generate_latex_hash(format, latex):
    return "<<{}||{}>>".format(format, latex)

def _mock__get_available_latex_elements(formulas):
    return {}

def _mock__get_latex_html(element):
    return element.hash


class ConverterV1TestCase(TestCase):
    def setUp(self):
        self.attachments = [
            _mock__attachment("first.png"),
            _mock__attachment("second.png"),
        ]

    # TODO: move to skoljka custom TestCase
    def assertEqualPrint(self, received, expected):
        if received != expected:
            print
            print "Received: ", received
            print "Expected: ", expected
            self.fail("Received != Expected")

    # def _get_converter(self, type, input, warnings=True,
    #         converter_mock=Converter):
    #     return converter_mock(type, input, self.attachments,
    #             url_prefix=MOCK_URL_PREFIX, warnings=warnings)

    def assertTokenization(self, input, expected_tokens, *args, **kwargs):
        tokenizer = Tokenizer(input, *args, **kwargs)
        tokens = tokenizer.tokenize()
        self.assertEqual(tokens, expected_tokens)

    def assertHTML(self, input, output, *args, **kwargs):
        self.assertHTMLLatex(input, output, None, *args, **kwargs)
        # # converter = self._get_converter(TYPE_HTML, input, *args, **kwargs)
        # html = convert(TYPE_HTML, input, attachments=self.attachments)
        # self.assertEqualPrint(html, output)

    def assertLatex(self, input, output, *args, **kwargs):
        self.assertHTMLLatex(input, None, output, *args, **kwargs)
        # # converter = self._get_converter(TYPE_LATEX, input, *args, **kwargs)
        # # i, latex = converter.convert()
        # latex = convert(TYPE_LATEX, input, attachments=self.attachments)
        # self.assertEqualPrint(latex, output)

    def assertHTMLLatex(self, input, output_html, output_latex,
            converter_kwargs={}, *args, **kwargs):
        tokenizer = Tokenizer(input)
        tokens = tokenizer.tokenize()
        converter = Converter(tokens, tokenizer, attachments=self.attachments,
                **converter_kwargs)
        converter.mock__generate_png = _mock__generate_png
        converter.mock__generate_latex_hash = _mock__generate_latex_hash
        converter.mock__get_available_latex_elements = _mock__get_available_latex_elements
        converter.mock__get_latex_html = _mock__get_latex_html
        if output_html is not None:
            self.assertEqualPrint(converter.convert_to_html(), output_html)
        if output_latex is not None:
            self.assertEqualPrint(converter.convert_to_latex(), output_latex)
        # self.assertHTML(input, output_html, *args, **kwargs)
        # self.assertLatex(input, output_latex, *args, **kwargs)

    def assertHTMLAutoLatex(self, input, output_html, *args, **kwargs):
        self.assertHTMLLatex(input, output_html, input, *args, **kwargs)
        # self.assertHTML(input, output_html, *args, **kwargs)
        # self.assertLatex(input, input, *args, **kwargs)

    def test_tokenization(self):
        self.assertTokenization("bla", [TokenText("bla")])
        self.assertTokenization("bla  bla", [TokenText("bla  bla")])
        self.assertTokenization("bla\n  bla", [
                TokenText("bla"),
                TokenSimpleWhitespace("\n  "),
                TokenText("bla"),
        ])
        self.assertTokenization("bla \n \n   bla", [
                TokenText("bla"),
                TokenMultilineWhitespace(" \n \n   "),
                TokenText("bla"),
        ])
        self.assertTokenization(
            "bla $a + b = c$ \n$$d*f+g  $$ dummy$$$$$$$$$a+b$\n  bla", [
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
        ])
        self.assertTokenization(
            "bla \( a+b  \)\n\n\[\n   c*d\n\]\n\nbla bla", [
                TokenText("bla"),
                TokenSimpleWhitespace(" "),
                TokenMath('\(%s\)', " a+b  "),
                TokenMultilineWhitespace("\n\n"),
                TokenMath('\[%s\]', "\n   c*d\n"),
                TokenMultilineWhitespace("\n\n"),
                TokenText("bla bla"),
        ])

        self.assertTokenization("\\\\ \\\\", [
                # Not sure about this one.
                TokenCommand('\\', whitespace=[" "]),
                TokenCommand('\\'),
        ])
        self.assertTokenization(
            "\\textasciicircum\\textasciitilde  \\textbackslash", [
                TokenCommand('textasciicircum'),
                TokenCommand('textasciitilde', whitespace=["  "]),
                TokenCommand('textbackslash'),
        ])
        self.assertTokenization( "bla\\unknownname bla", [
                TokenText("bla"),
                TokenError(SKIP, "\\unknownname"),
                TokenSimpleWhitespace(" "),
                TokenText("bla"),
        ])
        self.assertTokenization(
            # Comment picks all the leading whitespace from the next line.
            "bla\r\n% a comment\n   blabla % another comment", [
                TokenText("bla"),
                TokenSimpleWhitespace("\r\n"),
                TokenComment(" a comment\n   "),
                TokenText("blabla"),
                TokenSimpleWhitespace(" "),
                TokenComment(" another comment")
        ])
        self.assertTokenization(r"\url{bla}", [TokenCommand('url', 0, ["bla"])])
        self.assertTokenization(r"\url{b%la}", [TokenCommand('url', 0, ["b%la"])])
        self.assertTokenization(r"\url{b{}%la}", [TokenCommand('url', 0, ["b{}%la"])])
        self.assertTokenization(r"\url  {bla}", [TokenCommand('url', 0, ["bla"], ["  "])])
        self.assertTokenization(r"\url", [TokenError(SKIP, r"\url")])
        self.assertTokenization(r"\url bla", [
                TokenError(SKIP, r"\url"),
                TokenText("bla"),
        ])
        self.assertTokenization("\\href  {http://www.google.com} \n  {bla}", [
                TokenCommand('href', 0,
                    ["http://www.google.com", [TokenText("bla")]],
                    ["  ", " \n  "]),
                TokenText("bla"),
                TokenCommand('href', 1,
                    ["http://www.google.com", [TokenText("bla")]],
                    ["  ", " \n  "]),
        ])
        self.assertTokenization(r"\href{http://ww%w.g{}oogle.com}{bla}", [
                TokenCommand('href', 0, ["http://ww%w.g{}oogle.com", [TokenText("bla")]]),
                TokenText("bla"),
                TokenCommand('href', 1, ["http://ww%w.g{}oogle.com", [TokenText("bla")]]),
        ])
        self.assertTokenization(r"\href{http://ww%w.g{}oogle.com}", [
                TokenError(SKIP, r"\href{http://ww%w.g{}oogle.com}"),
        ])
        self.assertTokenization(r"\href{http://ww%w.g{}oogle.com}{bl%a}", [
                TokenError(SKIP, r"\href{http://ww%w.g{}oogle.com}{bl%a}"),
        ])
        self.assertTokenization(r"\emph{bla}", [
                TokenCommand('emph', 0, SKIP),
                TokenText("bla"),
                TokenCommand('emph', 1, SKIP),
        ])
        self.assertTokenization(r"\textbf{bla \sout{asdf}\uline{bla bla}}", [
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
        ])
        self.assertTokenization(r"\includegraphics[width=100pt]{image.png}", [
                TokenCommand('includegraphics', 0, ["width=100pt", "image.png"]),
        ])
        self.assertTokenization(
            "\\begin{center}\n  some content\n\\end{center}", [
                TokenCommand('begin', 0,
                    ['center', LatexEnvironmentDiv('mc-center')], ['']),
                TokenSimpleWhitespace("\n  "),
                TokenText("some content"),
                TokenSimpleWhitespace("\n"),
                TokenCommand('end', 0,
                    ['center', LatexEnvironmentDiv('mc-center')], ['']),
        ])
        self.assertTokenization(
            "\\begin{asdf}bla\\end{asdf}", [
                TokenError(SKIP, 'asdf'),
                TokenText("bla"),
                TokenError(SKIP, ''),
        ])

        # Test empty {}.
        self.assertTokenization("\\textasciicircum \n  bla", [
                TokenCommand('textasciicircum', whitespace=[" \n  "]),
                TokenText("bla"),
        ])
        self.assertTokenization("\\textasciicircumbla", [
                TokenError(SKIP, "\\textasciicircumbla"),
        ])
        self.assertTokenization("\\textasciicircum{}  bla", [
                TokenCommand('textasciicircum', 0),
                TokenOpenCurly(),
                TokenClosedCurly(),
                TokenSimpleWhitespace("  "),
                TokenText("bla"),
        ])

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
            r'\end{figure}', [
                TokenCommand('begin', 0, ['figure', _figure]),
                TokenCommand('begin', 0, ['flushleft', _flushleft]),
                TokenCommand('includegraphics', 0, [None, 'first.png']),
                TokenCommand('end', 0, ['flushleft', _flushleft]),
                TokenCommand('caption', 0, [[TokenText("Some caption here.")], "1"]),
                TokenText("Some caption here."),
                TokenCommand('caption', 1, [[TokenText("Some caption here.")], "1"]),
                TokenCommand('label', 0, ["some-label", ""]),
                TokenCommand('end', 0, ['figure', _figure]),
        ])

        _figure = LatexEnvironmentFigure(centering=True, tag="1")
        self.assertTokenization(
            r'\begin{figure}'
            r'\includegraphics{first.png}'
            r'\caption{Some caption here.}'
            r'\label{some-label}'
            r'\centering'
            r'\end{figure}', [
                TokenCommand('begin', 0, ['figure', _figure]),
                TokenCommand('includegraphics', 0, [None, 'first.png']),
                TokenCommand('caption', 0, [[TokenText("Some caption here.")], "1"]),
                TokenText("Some caption here."),
                TokenCommand('caption', 1, [[TokenText("Some caption here.")], "1"]),
                TokenCommand('label', 0, ["some-label", ""]),
                TokenCommand('centering', 0),
                TokenCommand('end', 0, ['figure', _figure]),
        ])

        _figure = LatexEnvironmentFigure(centering=True, tag="1")
        self.assertTokenization(
            r'\begin{figure}'
            r'\includegraphics{first.png}'
            r'\label{wrong-order}'
            r'\caption{Some caption here.}'
            r'\centering'
            r'\end{figure}', [
                TokenCommand('begin', 0, ['figure', _figure]),
                TokenCommand('includegraphics', 0, [None, 'first.png']),
                TokenCommand('label', 0, ["wrong-order", TokenError(SKIP, "")]),
                TokenCommand('caption', 0, [[TokenText("Some caption here.")], "1"]),
                TokenText("Some caption here."),
                TokenCommand('caption', 1, [[TokenText("Some caption here.")], "1"]),
                TokenCommand('centering', 0),
                TokenCommand('end', 0, ['figure', _figure]),
        ])

        # BBCode
        self.assertTokenization("[]", [TokenText("["), TokenText("]")])
        self.assertTokenization("[unknown tag]",
                [TokenText("["), TokenText("unknown tag"), TokenText("]")])
        self.assertTokenization("[b]bla[/b]", [
                TokenBBCode('b', {'b': None}, 0, 3),
                TokenText("bla"),
                TokenBBCode('b', None, 6, 10),
        ])
        self.assertTokenization("[/b]bla[b bla=\"xy\\\"z\"]", [
                TokenBBCode('b', None, 0, 4),
                TokenText("bla"),
                TokenBBCode('b', {'b': None, 'bla': "xy\"z"}, SKIP, SKIP),
        ])

        self.assertTokenization("[url=http://www.example.com/]title[/url]", [
                TokenBBCode('url', {'url': 'http://www.example.com/'}, 0, SKIP),
                TokenText("title"),
                TokenBBCode('url', None, SKIP, SKIP),
        ])
        self.assertTokenization("[url]http://www.example.com/[/url]", [
                TokenBBCode('url', {'url': None}, 0, SKIP, "http://www.example.com/"),
        ])



    def test_latex_commands(self):
        # Newlines are always seperated as TokenSimpleWhitespace, which then
        # is replaced with a single whitespace (for HTML that is enough).
        self.assertHTMLAutoLatex("bla", "bla")
        self.assertHTMLAutoLatex("bla\nbla", "bla bla")
        self.assertHTMLAutoLatex("bla\n\nbla", "bla<br>bla")
        self.assertHTMLAutoLatex("bla  \n\n  bla", "bla<br>bla")
        self.assertHTMLAutoLatex("bla  \n \n \n\n  bla", "bla<br>bla")
        self.assertHTMLAutoLatex("bla\n\n\n\nbla", "bla<br>bla")

        self.assertHTMLAutoLatex(
                r"a\-very\-very\-long\-word\-here",
                r"averyverylongwordhere")
        self.assertHTMLAutoLatex( r"\TeX", r"<<$%s$||\TeX>>")
        self.assertHTMLAutoLatex( r"\LaTeX", r"<<$%s$||\LaTeX>>")

        self.assertHTMLAutoLatex("bla\\\\  asdf", "bla<br>asdf")
        self.assertHTMLAutoLatex("\\emph{bla bla bla}", "<i>bla bla bla</i>")
        self.assertHTMLAutoLatex("\\emph  {bla \\textbf \n{bla} bla}",
                        "<i>bla <b>bla</b> bla</i>")

        self.assertHTMLAutoLatex(
                "\\href{http://www.example.com/bla%40bla}{click here}",
                '<a href="http://www.example.com/bla%40bla" rel="nofollow">'
                    'click here</a>')
        self.assertHTMLAutoLatex(
                "\\url{http://www.example.com/}",
                '<a href="http://www.example.com/" rel="nofollow">'
                    'http://www.example.com/</a>')
        self.assertHTMLAutoLatex(
                "\\url{http://www.example.com/bla%40bla}",
                '<a href="http://www.example.com/bla%40bla" rel="nofollow">'
                    'http://www.example.com/bla%40bla</a>')

        # Note: Look at setUp for mocked attachments.
        self.assertHTMLAutoLatex(
                "\\includegraphics{first.png}",
                '<img src="/mock/first.png" alt="Attachment first.png" class="latex">')

        # TODO: Check if the conversion pt->px makes any sense.
        self.assertHTMLAutoLatex(
                "\\includegraphics  [width=100pt] {first.png}",
                '<img src="/mock/first.png" alt="Attachment first.png" class="latex" width="100">')
        self.assertHTMLAutoLatex(
                "\\includegraphics[width=100pt,height=200pt]{first.png}",
                '<img src="/mock/first.png" alt="Attachment first.png" class="latex" width="100" height="200">')
        self.assertHTMLAutoLatex(
                "\\includegraphics[scale=0.7]{first.png}",
                '<img src="/mock/first.png" alt="Attachment first.png" class="latex" width="70%" height="70%">')
        self.assertHTMLAutoLatex(
                "\\includegraphics[scale=0.7123]{first.png}",
                '<img src="/mock/first.png" alt="Attachment first.png" class="latex" width="71.23%" height="71.23%">')

        self.assertHTMLAutoLatex("bla\\textasciicircum{}asdf", "bla^asdf")
        self.assertHTMLAutoLatex("bla\\textasciicircum{}asdf", "bla^asdf")
        self.assertHTMLAutoLatex("bla\\textasciitilde{}asdf", "bla~asdf")
        self.assertHTMLAutoLatex("something\\textbackslash{}something",
                        "something\\something")

        # Simple containers.
        self.assertHTMLAutoLatex(
                "\\fbox{do not wrap this part}",
                '<span class="mc-fbox">do not wrap this part</span>')
        self.assertHTMLAutoLatex(
                "\\mbox{do not wrap this part}",
                '<span class="mc-mbox">do not wrap this part</span>')
        self.assertHTMLAutoLatex("\\textbf{bla bla bla}", "<b>bla bla bla</b>")
        self.assertHTMLAutoLatex("\\textit{bla bla bla}", "<i>bla bla bla</i>")
        self.assertHTMLAutoLatex(
                "\\underline{underlined with nowrap}",
                '<span class="mc-underline">underlined with nowrap</span>')
        self.assertHTMLAutoLatex("asdf \\sout{bla bla} qwerty \\uline{asdf}",
                        "asdf <s>bla bla</s> qwerty <u>asdf</u>")
        self.assertHTMLAutoLatex("bla\\~{}asdf", "bla~asdf")
        self.assertHTMLAutoLatex("bla\\~{}asdf", "bla~asdf")

        # Begin commands.
        self.assertHTMLAutoLatex("\\begin{center}\\textbf{bla}\\end{center}",
                        '<div class="mc-center"><b>bla</b></div>')
        self.assertHTMLAutoLatex("\\begin\n{center}\\textbf  {bla}\\end \n{center}",
                        '<div class="mc-center"><b>bla</b></div>')
        # Math mode.
        self.assertHTMLAutoLatex("$a+b$", "<<$%s$||a+b>>")
        self.assertHTMLAutoLatex("\(a+b\)", "<<\(%s\)||a+b>>")
        self.assertHTMLAutoLatex("\[ a+b \]", "<<\[%s\]|| a+b >>")
        self.assertHTMLAutoLatex("$$  a+b $$", "<<$$%s$$||  a+b >>")

        # Figures and environment testing.
        self.assertHTMLAutoLatex(
            r'\begin{figure}'
            r'\includegraphics{first.png}'
            r'\caption{Some caption here.}'
            r'\label{some-label}'
            r'\centering'
            r'\end{figure}',
            '<div class="mc-figure mc-center">'
            '<img src="/mock/first.png" alt="Attachment first.png" class="latex">'
            '<div class="mc-caption"><span class="mc-caption-tag">Slika 1:</span> Some caption here.</div>'
            '</div>'
        )


        # Complex example.
        self.assertHTMLAutoLatex(
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
                '<div class="mc-caption"><span class="mc-caption-tag">Slika 2:</span> Another caption here.</div>'
                '</div>'
                ''
                'First: <<$%s$||1>>'
                'Second: <<$%s$||??>>',
                converter_kwargs={'errors_enabled': False})

    # # def test_bla(self):
    # #     #self.assertHTMLAutoLatex("", "")
    # #     pass



    def test_bbcode(self):
        self.assertEqual(parse_bbcode("[b]", 0), ('b', {'b': None}, 3))
        self.assertEqual(parse_bbcode("[b]bla", 0), ('b', {'b': None}, 3))
        self.assertEqual(parse_bbcode("[/b]bla", 0), ('b', None, 4))
        self.assertRaises(BBCodeException, lambda : parse_bbcode("[/b=5]", 0))
        self.assertRaises(BBCodeException, lambda : parse_bbcode("[/b asdf]", 0))
        self.assertEqual(
                parse_bbcode("[asdf=bla]x", 0),
                ('asdf', {'asdf': "bla"}, 10))
        self.assertEqual(
                parse_bbcode("[abc def=ghi]x", 0),
                ('abc', {'abc': None, 'def': "ghi"}, 13))
        self.assertEqual(
                parse_bbcode("[abc def=ghi asdf]x", 0),
                ('abc', {'abc': None, 'def': "ghi", 'asdf': None}, 18))
        self.assertEqual(
                parse_bbcode("[abc def='ghi \\'asdf']x", 0),
                ('abc', {'abc': None, 'def': "ghi 'asdf"}, 22))
        self.assertRaises(
                BBCodeException,
                lambda : parse_bbcode("[abc def='ghi \\'as\\\\'df']x", 0))
        self.assertEqual(
                parse_bbcode("[abc def=\"ghi a\\'\\\"sdf\"]x", 0),
                ('abc', {'abc': None, 'def': "ghi a\\'\"sdf"}, 24))
        self.assertEqual(
                parse_bbcode("[abc def=\"][[]][\"]x", 0),
                ('abc', {'abc': None, 'def': "][[]]["}, 18))

        self.assertHTMLLatex(
                "[b]bla[/b]",
                "<b>bla</b>",
                "\\textbf{bla}")
        self.assertHTMLLatex(
                "Is this [b]example [i]working[/i][/b]?",
                "Is this <b>example <i>working</i></b>?",
                "Is this \\textbf{example \\emph{working}}?")
        self.assertHTMLLatex(
                "A [b]complex [i]example[/i] [s]bla[u]asdf[/u][/s][/b]",
                "A <b>complex <i>example</i> <s>bla<u>asdf</u></s></b>",
                "A \\textbf{complex \\emph{example} \\sout{bla\\uline{asdf}}}")
        self.assertHTMLLatex(
                "[center]This is centered[/center]",
                '<div class="mc-center">This is centered</div>',
                "\\begin{center}This is centered\\end{center}")
        self.assertHTMLLatex(
                "[img attachment=1]",
                '<img src="/mock/first.png" alt="Attachment #1" class="latex">',
                "\\includegraphics{first.png}")
        self.assertHTMLLatex(
                "[img attachment=1 width=200px]",
                '<img src="/mock/first.png" alt="Attachment #1" class="latex" width="200">',
                "\\includegraphics[width=200pt]{first.png}")
        self.assertHTMLLatex(
                "[img attachment=1 height=300px]",
                '<img src="/mock/first.png" alt="Attachment #1" class="latex" height="300">',
                "\\includegraphics[height=300pt]{first.png}")
        self.assertHTMLLatex(
                "[img attachment=1 scale=0.6]",
                '<img src="/mock/first.png" alt="Attachment #1" class="latex" width="60%" height="60%">',
                "\\includegraphics[scale=0.6]{first.png}")
        self.assertHTMLLatex(
                "[quote]bla bla[/quote]",
                '<div class="mc-quote">bla bla</div>',
                "bla bla")
    #     self.assertHTMLLatex(
    #             "[ref=5 task=123](click here)[/ref]",
    #             r'<<$%s$||5>><a href="http://mock.com/task/123/ref/" rel="nofollow">(click here)</a>',
    #             r"$5$\href{http://mock.com/task/123/ref/}{(click here)}",
    #             converter_mock=ConverterMock)
    #     self.assertHTMLLatex(
    #             "[ref=5 task=123 page=3](click here)[/ref]",
    #             r'<<$%s$||5>><a href="http://mock.com/task/123/ref/?page=3" rel="nofollow">(click here)</a>',
    #             r"$5$\href{http://mock.com/task/123/ref/?page=3}{(click here)}",
    #             converter_mock=ConverterMock)
        self.assertHTMLLatex(
                "[url]http://example.com/[/url]",
                '<a href="http://example.com/" rel="nofollow">http://example.com/</a>',
                "\\url{http://example.com/}")
        self.assertHTMLLatex(
                "[url=http://example.com/]click here[/url]",
                '<a href="http://example.com/" rel="nofollow">click here</a>',
                "\\href{http://example.com/}{click here}")

    def test_latex_formula(self):  # Test $ ... $ etc.
        self.assertHTMLLatex(
                "$bla$",
                "<<$%s$||bla>>",
                "$bla$")
        self.assertHTMLLatex(
                "\[bla\]",
                "<<\[%s\]||bla>>",
                "\[bla\]")
        self.assertHTMLLatex(
                "$$$bla$$$",
                "<<%s||bla>>",
                "bla")
        self.assertHTMLLatex(
                "bla $$$something $a + b = c$ bla $$d + e = f$$ $$$ bla",
                "bla <<%s||something $a + b = c$ bla $$d + e = f$$ >> bla",
                "bla something $a + b = c$ bla $$d + e = f$$  bla")
        self.assertHTMLLatex(
                "\(bla\)",
                "<<\(%s\)||bla>>",
                "\(bla\)")
        self.assertHTMLLatex(
                "\[bla\]",
                "<<\[%s\]||bla>>",
                "\[bla\]")

    # def test_labels(self):
    #     """Test \\label and \\ref."""
    #     self.assertHTMLAutoLatex(
    #             r"\begin{equation}\label{first}x = y + z\end{equation}" \
    #             r"ref to equation \ref{first}" \
    #             r"\begin{equation}\label{second}a = b + c\end{equation}" \
    #             r"ref to equation \ref{second}",
    #             r'<div class="mc-center"><<%s||\begin{equation}\tag{1}\label{first}x = y + z\end{equation}>></div>' \
    #             r'ref to equation <<$%s$||1>>' \
    #             r'<div class="mc-center"><<%s||\begin{equation}\tag{2}\label{second}a = b + c\end{equation}>></div>' \
    #             r'ref to equation <<$%s$||2>>',
    #             converter_mock=ConverterMock)
