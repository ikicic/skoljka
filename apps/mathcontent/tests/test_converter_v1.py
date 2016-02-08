from django.test import TestCase

from mathcontent.converter_v1 import Converter
from mathcontent.models import TYPE_HTML, TYPE_LATEX

def _mock_attachment(filename):
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

class MathContentRenderTestCase(TestCase):
    def setUp(self):
        self.attachments = [
            _mock_attachment("first.png"),
            _mock_attachment("second.png"),
        ]

    def assertHTML(self, input, output, converter_mock=Converter):
        converter = converter_mock(TYPE_HTML, input, self.attachments)
        i, html = converter.convert()
        self.assertEqual(html, output)

    def assertLatex(self, input, output, converter_mock=Converter):
        converter = converter_mock(TYPE_LATEX, input, self.attachments)
        i, html = converter.convert()
        self.assertEqual(html, output)

    def assertHTMLLatex(self, input, output_html, output_latex, *args, **kwargs):
        self.assertHTML(input, output_html, *args, **kwargs)
        self.assertLatex(input, output_latex, *args, **kwargs)

    def assertHTMLAutoLatex(self, input, output_html, *args, **kwargs):
        self.assertHTML(input, output_html, *args, **kwargs)
        self.assertLatex(input, input, *args, **kwargs)

    def test_latex_commands(self):
        self.assertHTMLAutoLatex("bla", "bla")
        self.assertHTMLAutoLatex("bla\nbla", "bla\nbla")
        self.assertHTMLAutoLatex("bla\n\nbla", "bla<br>bla")
        # First spaces are copies (it's not important how do they behave).
        self.assertHTMLAutoLatex("bla  \n\n  bla", "bla  <br>bla")
        self.assertHTMLAutoLatex("bla  \n \n \n\n  bla", "bla  <br>bla")
        self.assertHTMLAutoLatex("bla\n\n\n\nbla", "bla<br>bla")

        self.assertHTMLAutoLatex("bla\\\\asdf", "bla<br>asdf")
        self.assertHTMLAutoLatex("\\emph{bla bla bla}", "<i>bla bla bla</i>")
        self.assertHTMLAutoLatex("\\emph{bla \\textbf{bla} bla}",
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

        self.assertHTMLAutoLatex(
                "\\includegraphics{first.png}",
                '<img src="/mock/first.png" alt="Attachment first.png" class="latex">')
        # TODO: Check if the conversion pt->px makes any sense.
        self.assertHTMLAutoLatex(
                "\\includegraphics[width=100pt]{first.png}",
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
        self.assertHTMLAutoLatex("\\textbf{bla bla bla}", "<b>bla bla bla</b>")
        self.assertHTMLAutoLatex("asdf \\sout{bla bla} qwerty \\uline{asdf}",
                        "asdf <s>bla bla</s> qwerty <u>asdf</u>")
        self.assertHTMLAutoLatex("bla\\~{}asdf", "bla~asdf")
        self.assertHTMLAutoLatex("bla\\~{}asdf", "bla~asdf")

        # Begin commands.
        self.assertHTMLAutoLatex("\\begin{center}\\textbf{bla}\\end{center}",
                        '<div class="mc-center"><b>bla</b></div>')

    def test_bbcode(self):
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
        self.assertHTMLLatex(
                "[url]http://example.com/[/url]",
                '<a href="http://example.com/" rel="nofollow">http://example.com/</a>',
                "\\url{http://example.com/}")
        self.assertHTMLLatex(
                "[url=http://example.com/]click here[/url]",
                '<a href="http://example.com/" rel="nofollow">click here</a>',
                "\\href{http://example.com/}{click here}")

    def test_latex_formula(self):  # Test $ ... $ etc.
        class ConverterMock(Converter):
            def get_latex_picture(self, format, latex):
                return "<<{}||{}>>".format(format, latex)

        self.assertHTMLLatex(
                "$bla$",
                "<<$%s$||bla>>",
                "$bla$",
                converter_mock=ConverterMock)
        self.assertHTMLLatex(
                "$$bla$$",
                "<<\[%s\]||bla>>",
                "\[bla\]",
                converter_mock=ConverterMock)
        self.assertHTMLLatex(
                "$$$bla$$$",
                "<<%s||bla>>",
                "bla",
                converter_mock=ConverterMock)
        self.assertHTMLLatex(
                "bla $$$something $a + b = c$ bla $$d + e = f$$ $$$ bla",
                "bla <<%s||something $a + b = c$ bla $$d + e = f$$ >> bla",
                "bla something $a + b = c$ bla $$d + e = f$$  bla",
                converter_mock=ConverterMock)
        self.assertHTMLLatex(
                "\(bla\)",
                "<<\(%s\)||bla>>",
                "\(bla\)",
                converter_mock=ConverterMock)
        self.assertHTMLLatex(
                "\[bla\]",
                "<<\[%s\]||bla>>",
                "\[bla\]",
                converter_mock=ConverterMock)
