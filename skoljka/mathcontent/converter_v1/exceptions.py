from django.utils.translation import ugettext as _


class BBCodeException(Exception):
    pass


class BBUnexpectedParameters(BBCodeException):
    def __init__(self, param=None):
        if param is None:
            msg = _("Unexpected parameter(s).")
        else:
            msg = _("Unexpected parameter:") + " " + param
        super(BBUnexpectedParameters, self).__init__(msg)


class LatexValueError(Exception):
    pass


class ParseError(Exception):
    pass


class ParserInternalError(Exception):
    pass
