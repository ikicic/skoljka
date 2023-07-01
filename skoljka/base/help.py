from django.utils.translation import ugettext as _

from skoljka.mathcontent.converter_v1 import default_parindent, default_parskip
from skoljka.mathcontent.models import TYPE_HTML, TYPE_LATEX
from skoljka.mathcontent.utils import convert_safe
from skoljka.utils.decorators import response

_evaluate__cache = {}


def _evaluate(type, content):
    try:
        return _evaluate__cache[(type, content)]
    except KeyError:
        result = convert_safe(type, content)
        _evaluate__cache[(type, content)] = result
        return result


@response('help/help_format.html')
def help_format(request):
    INFO_FORMAT = u" <span style=\"color:gray;font-style:italic;\">{}</span>"
    PARTIAL = INFO_FORMAT.format(_("Partially supported."))
    INCOMPATIBLE = INFO_FORMAT.format(_("Possibly incompatible behavior."))
    VISUALLY_DIFFERENT = INFO_FORMAT.format(
        _("Visually different when exported to PDF.")
    )
    INCOMPLETE = "<<INCOMPLETE-IMPLEMENTATION>>"
    commands = [
        _("Basic Commands"),
        ('\\emph', _("Emphasized text (usually italic)."), "\\emph{TEXT}"),
        ('\\textbf', _("Bold."), "\\textbf{TEXT}"),
        ('\\textit', _("Italic."), "\\textit{TEXT}"),
        ('\\sout', _("Strikethrough."), "\\sout{TEXT}"),
        ('\\uline', _("Underline."), "\\uline{TEXT}"),  # a)
        (
            '\\underline',
            _(
                "Underline and disable word-wrap. "
                "It's recommended to use <code>\\uline</code> instead."
            ),
            "\\underline{TEXT}",
        ),  # a)
        ('\\texttt', _("Monospace font.") + VISUALLY_DIFFERENT, "\\texttt{TEXT}"),
        ('\\\\', _("Newline.") + INCOMPATIBLE, "a\\\\b"),
        _("Advanced Commands"),
        (
            '\\includegraphics',
            _("Show the given image.") + PARTIAL + INCOMPLETE,
            "",
        ),  # b)
        ('\\caption', _("Figure caption.") + INCOMPLETE, ""),  # b)
        ('\\centering', _("Figure centering.") + INCOMPLETE, ""),  # b)
        (
            '\\label',
            _("Set figure or equation label.") + PARTIAL + INCOMPLETE,
            "",
        ),  # b)
        (
            '\\ref',
            _("Given a label, show a link to the related content.")
            + PARTIAL
            + INCOMPLETE,
            "",
        ),  # TODO
        ('\\url', _("Link"), "\\url{http://www.example.com/}"),
        ('\\href', _("Link"), "\\href{http://www.example.com/}{TEXT}"),
        (
            '\\setlength',
            _(
                "Set value of the given length command. Currently, only "
                "<code>\\parindent</code> and <code>\\parskip</code> are "
                "supported, representing indentation length and paragraph "
                "top margin."
            )
            + " "
            + _("Note that the first paragraph is not indented.")
            + " "
            + _(
                u"The default values are <code>%(parskip)s</code> for "
                "<code>\\parskip</code> and <code>%(parindent)s</code> for "
                "<code>\\parindent</code>."
            )
            % {
                'parskip': default_parskip,
                'parindent': default_parindent,
            },
            "\\setlength{\\parskip}{3em}\n"
            "\\setlength{\\parindent}{2em}\n\n"
            "First paragraph\n\n"
            "Second paragraph",
        ),
        _("Other Commands"),
        (
            "\\fbox",
            _("Framed box with disabled word-wrap.") + " " + _("Please don't misuse."),
            "\\fbox{TEXT}",
        ),
        (
            "\\mbox",
            _("Disabled word-wrap.") + " " + _("Please don't misuse."),
            "\\mbox{TEXT}",
        ),
        ("\\TeX", "", None),
        ("\\LaTeX", "", None),
        ("\\textasciicircum", _("Symbol %s.") % '^' + PARTIAL, None),
        ("\\textasciitilde", _("Symbol %s.") % '~' + PARTIAL, None),
        ("\\textbackslash", _("Symbol %s.") % '\\' + PARTIAL, None),  # Partial?
        (
            "\\-",
            _("Soft hyphen, shown in HTML as <pre>&amp;shy;</pre>."),
            "a\-very\-long\-word",
        ),
        ("\\{", _("Symbol %s.") % '{', None),
        ("\\}", _("Symbol %s.") % '}', None),
        ("\\%", _("Symbol %s.") % '%', None),
        ("\\_", _("Symbol %s.") % '_', None),
        ("\\&", _("Symbol %s.") % '&', None),
        ("\\$", _("Symbol %s.") % '$', None),
        ("\\#", _("Symbol %s.") % '#', None),
        _("LaTeX Environments"),
        (
            "\\begin{center}...\\end{center}",
            _("Centering."),
            "\\begin{center}TEXT\\end{center}",
        ),
        (
            "\\begin{figure}...\\end{figure}",
            _("Figure, used for inserting images."),
            "",
        ),
        (
            "\\begin{flushleft}...\\end{flushleft}",
            "",
            "\\begin{flushleft}TEXT\\\\TEXT TEXT\\end{flushleft}",
        ),
        (
            "\\begin{flushright}...\\end{flushright}",
            "",
            "\\begin{flushright}TEXT\\\\TEXT TEXT\\end{flushright}",
        ),
        (
            "\\begin{verbatim}...\\end{verbatim}",
            _("Pre-formatted text.") + VISUALLY_DIFFERENT,
            "\\begin{verbatim}a = b + c\n  = c + b\\end{verbatim}",
        ),
        (
            "\\begin{verbatim*}...\\end{verbatim*}",
            _("Similar to <code>verbatim</code>, where spaces are shown as &blank;.")
            + VISUALLY_DIFFERENT,
            "\\begin{verbatim*}a = b + c\n  = c + b\\end{verbatim*}",
        ),
    ]

    bbcode_commands = [
        ('[b]...[/b]', _("Bold."), "[b]TEXT[/b]"),
        ('[i]...[/i]', _("Italic."), "[i]TEXT[/i]"),
        ('[s]...[/s]', _("Strikethrough."), "[s]TEXT[/s]"),
        ('[u]...[/u]', _("Underline."), "[u]TEXT[/u]"),
        ('[code]...[/code]', _("Code."), "[code]TEXT[/code]"),
        (
            '[hide]...[/hide]',
            _("Hidden text.") + VISUALLY_DIFFERENT,
            "[hide]TEXT[/hide]",
        ),
        (
            '[hide=text]...[/hide]',
            _("Hidden text.") + VISUALLY_DIFFERENT,
            "[hide=\"Link text\"]TEXT[/hide]",
        ),
        (
            '[par SKIP INDENT]',
            _(
                "Shorthand for <code>\\setlength{\\parskip}{SKIP} "
                "\\setlength{\\parindent}{INDENT}</code>. "
                "Value <code>0</code> is treated as <code>0pt</code>."
            ),
            "[par 1em 0]",
        ),
        (
            '[pre]...[/pre]',
            _(
                "Preformatted text. Simulates LaTeX environment "
                "<code>verbatim</code>."
            ),
            "[pre]TEXT\n    TEXT[/pre]",
        ),
        ('[quote]...[/quote]', _("Quotation."), "[quote]TEXT[/quote]"),
        (
            '[img attachment=x '
            '<span style=\"color:gray;\">width=300px height=300px</span>]',
            _(
                "Show the attachment #x, counting from 1. Optionally, specify "
                "the width and height."
            )
            + " "
            + _("Please don't misuse.")
            + INCOMPLETE,
            None,
        ),
        ('[url]...[/url]', _("Link."), "[url]http://www.google.com/[/url]"),
        (
            '[url=<url>]...[/url]',
            _("Link."),
            "[url=http://www.google.com/]Google[/url]",
        ),
    ]

    # TODO: Write an example.

    def _replace_text(text):
        return text.replace('TEXT', _("Some text here."))

    class CommandHelp(object):
        def __init__(self, name, description, example):
            description = _replace_text(description)
            example = name if example is None else _replace_text(example)
            self.name = name
            self.description = description.replace(
                INCOMPLETE, INFO_FORMAT.format(_("Incomplete."))
            )
            self.example = example
            self.evaluated = example and _evaluate(TYPE_HTML, example)
            self.incomplete = INCOMPLETE in description

    command_groups = []
    for cmd in commands:
        if isinstance(cmd, tuple):
            name, description, example = cmd
            command_groups[-1][1].append(CommandHelp(name, description, example))
        else:
            # (Group name, list of commands).
            command_groups.append((cmd, []))

    class BBCodeCommandHelp(object):
        def __init__(self, info):
            self.format = info[0]
            self.description = info[1].replace(
                INCOMPLETE, INFO_FORMAT.format(_("Incomplete."))
            )
            example = info[2] and _replace_text(info[2])
            self.example = example
            self.html = example and _evaluate(TYPE_HTML, example)
            self.latex = example and _evaluate(TYPE_LATEX, example)
            self.incomplete = INCOMPLETE in info[1]

    bbcode_commands_help = [BBCodeCommandHelp(x) for x in bbcode_commands]

    return {
        'command_groups': command_groups,
        'bbcode_commands_help': bbcode_commands_help,
    }
