from django import template

register = template.Library()

# @register.simple_tag
# def mathcontent_form_extra():
#     return  \
#        '<button type="button" class="mathcontent_preview_button btn">Pregled</button><br><br>' \
#        '<div class="mathcontent_preview well" style="display:none;"></div>'

@register.inclusion_tag('inc_mathcontent_attachments.html')
def mathcontent_attachments(content):
    return {'attachments': content.attachments.all()}

@register.inclusion_tag('inc_mathcontent_attachments_small.html')
def mathcontent_attachments_small(content=None, attachments=None):
    """
        List all attachments for given math content, or manually given
        attachments. The later case is useful when listing attachments
        of multiple tasks.

        Outputs the inline list of short links to those files.
    """
    if attachments is None:
        attachments = content.attachments.all()
    return {'attachments': attachments}
