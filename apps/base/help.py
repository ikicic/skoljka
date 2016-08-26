from django.utils.translation import ugettext as _

from mathcontent.models import TYPE_HTML, TYPE_LATEX
from mathcontent.utils import convert
from skoljka.libs.decorators import response

_evaluate__cache = {}
def _evaluate(type, content):
    try:
        return _evaluate__cache[(type, content)]
    except KeyError:
        result = convert(type, content)
        _evaluate__cache[(type, content)] = result
        return result


@response('help/help_format.html')
def help_format(request):
    INFO_FORMAT = " <span style=\"color:gray;font-style:italic;\">{}</span>"
    PARTIAL = INFO_FORMAT.format(_("Partial support."))
    INCOMPATIBLE = INFO_FORMAT.format(_("Possibly incompatible behavior."))
    commands = [
        _("Basic commands"),
        ('\\emph', _("Emphasized text (usually italic)"), "\\emph{TEXT}"),
        ('\\textbf', _("Bold"), "\\textbf{TEXT}"),
        ('\\textit', _("Italic"), "\\textit{TEXT}"),
        ('\\sout', _("Strikethrough"), "\\sout{TEXT}"),
        ('\\uline', _("Underline"), "\\uline{TEXT}"),         # a)
        ('\\underline',
            _("Underline and disable word-wrap. "
                "It's recommended to use <code>\\uline</code> instead."),
            "\\underline{TEXT}"), # a)
        ('\\\\', _("Newline") + INCOMPATIBLE, "a\\\\b"),
        _("Advanced commands"),
        ('\\includegraphics', _("Show images.") + PARTIAL, ""),  # b)
        ('\\caption', _("Figure caption."), ""),      # b)
        ('\\centering', _("Figure centering."), ""),  # b)
        ('\\label', _("Set figure or equation label. ") + PARTIAL, ""),  # b)
        ('\\ref', _("Given a label, show a link to the related content.")
                + PARTIAL, ""),  # TODO
        ('\\url', _("Link"), "\\url{http://www.example.com/}"),
        ('\\href', _("Link"), "\\href{http://www.example.com/}{TEXT}"),
        ('\\setlength',
            _("Set value of the given length command. Currently, only "
                "<code>\\parindent</code> and <code>\\parskip</code> are "
                "supported, representing indentation length and paragraph "
                "top margin.")
            + " " + _("Note that the first paragraph is not indented."),
            "\\setlength{\\parindent}{2em}\n"
            "\\setlength{\\parskip}{3em}\n\n"
            "First paragraph\n\n"
            "Second paragraph"),
        _("Other commands"),
        ("\\fbox",
            _("Framed box with disabled word-wrap.")
            + " " + _("Please don't misuse."),
            "\\fbox{TEXT}"),
        ("\\mbox",
            _("Disabled word-wrap.")
            + " " + _("Please don't misuse."),
            "\\mbox{TEXT}"),
        ("\\TeX", "", None),
        ("\\LaTeX", "", None),
        ("\\textasciicircum", _("Symbol %s.") % '^' + PARTIAL, None),
        ("\\textasciitilde", _("Symbol %s.") % '~' + PARTIAL, None),
        ("\\textbackslash", _("Symbol %s.") % '\\' + PARTIAL, None),  # Partial?
        ("\\~", _("Symbol %s.") % '~' + PARTIAL, None),
        ("\\-", _("Soft hyphen, shown in HTML as <pre>&amp;shy;</pre>."),
            "a\-very\-long\-word"),
    ]

    bbcode_commands = [
        ('[b]...[/b]', _("Bold"), "[b]TEXT[/b]"),
        ('[i]...[/i]', _("Italic"), "[i]TEXT[/i]"),
        ('[s]...[/s]', _("Strikethrough"), "[s]TEXT[/s]"),
        ('[u]...[/u]', _("Underline"), "[u]TEXT[/u]"),
        ('[quote]...[/quote]', _("Quote"), "[quote]TEXT[/quote]"),
        ('[img attachment=x '
            '<span style=\"color:gray;\">width=300px height=300px</span>]',
            _("Show the attachment #x, counting from 1. Optionally, specify "
                "the width and height.") + " " + _("Please don't misuse."),
            None),
        ('[url]...[/url]', _("Link"), "[url]http://www.google.com/[/url]"),
        ('[url=<url>]...[/url]', _("Link"),
            "[url=http://www.google.com/]Google[/url]")
    ]

    # TODO: a) Document what's the difference.
    # TODO: b) Write an example.

    def _replace_text(text):
        return text.replace('TEXT', _("Some text here."))

    class CommandHelp(object):
        def __init__(self, name, description, example):
            description = _replace_text(description)
            example = name if example is None else _replace_text(example)
            self.name = name
            self.description = description
            self.example = example
            self.evaluated = example and _evaluate(TYPE_HTML, example)

    command_groups = []
    for cmd in commands:
        if isinstance(cmd, tuple):
            name, description, example = cmd
            command_groups[-1][1].append(
                    CommandHelp(name, description, example))
        else:
            # (Group name, list of commands).
            command_groups.append((cmd, []))


    class BBCodeCommandHelp(object):
        def __init__(self, info):
            self.format = info[0]
            self.description = info[1]
            example = info[2] and _replace_text(info[2])
            self.example = example
            self.html = example and _evaluate(TYPE_HTML, example)
            self.latex = example and _evaluate(TYPE_LATEX, example)

    bbcode_commands_help = [BBCodeCommandHelp(x) for x in bbcode_commands]

    return {
        'command_groups': command_groups,
        'bbcode_commands_help': bbcode_commands_help
    }
