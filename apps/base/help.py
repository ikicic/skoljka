from django.utils.translation import ugettext as _

from mathcontent.utils import convert_to_html
from skoljka.libs.decorators import response

_evaluate__cache = {}
def _evaluate(content):
    try:
        return _evaluate__cache[content]
    except KeyError:
        html = convert_to_html(content)
        _evaluate__cache[content] = html
        return html


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
                "It's recommended to use \\uline instead."),
            "\\underline{TEXT}"), # a)
        ('\\\\', _("Newline") + INCOMPATIBLE, "a\\\\b"),
        _("Advanced commands"),
        ('\\includegraphics', _("Show images.") + PARTIAL, ""),  # b)
        ('\\caption', _("Figure caption."), ""),      # b)
        ('\\centering', _("Figure centering."), ""),  # b)
        ('\\label', _("Set figure or equation label. ") + PARTIAL, ""),  # b)
        ('\\ref', _("Given a label, show a link to the related content.") + \
                PARTIAL, ""),  # TODO
        ('\\url', _("Link"), "\\url{http://www.example.com/}"),
        ('\\href', _("Link"), "\\href{http://www.example.com/}{TEXT}"),
        ('\\setlength',
            _("Set value of the given length command. Currently, only "
                "\\parindent and \\parskip are supported, representing "
                "indentation length and paragraph top margin.") + " " +
            _("Note that the first paragraph is not indented."),
            "\\setlength{\\parindent}{2em}\n"
            "\\setlength{\\parskip}{3em}\n\n"
            "First paragraph\n\n"
            "Second paragraph"),
        _("Other commands"),
        ("\\fbox",
            _("Framed box with disabled word-wrap.") + " " +
            _("Please don't misuse."),
            "\\fbox{TEXT}"),
        ("\\mbox",
            _("Disabled word-wrap.") + " " +
            _("Please don't misuse."),
            "\\mbox{TEXT}"),
        ("\\TeX", "", None),
        ("\\LaTeX", "", None),
        ("\\textasciicircum", _("Symbol %s.") % '^' + PARTIAL, None),
        ("\\textasciitilde", _("Symbol %s.") % '~' + PARTIAL, None),
        ("\\textbackslash", _("Symbol %s.") % '\\' + PARTIAL, None),  # Partial?
        ("\\~", _("Symbol %s.") % '~' + PARTIAL, None),
        _("Ignored commands"),
        ("\\-", "", "a\-very\-long\-word"),
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
            self.evaluated = _evaluate(example) if example else example

    command_groups = []
    for cmd in commands:
        if isinstance(cmd, tuple):
            name, description, example = cmd
            command_groups[-1][1].append(
                    CommandHelp(name, description, example))
        else:
            # (Group name, list of commands).
            command_groups.append((cmd, []))

    return {'command_groups': command_groups}



