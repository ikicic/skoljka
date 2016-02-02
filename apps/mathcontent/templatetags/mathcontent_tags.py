from django import template
from django.utils.html import mark_safe

register = template.Library()

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


@register.inclusion_tag('inc_mathcontent_bootstrap_preview.html')
def mathcontent_bootstrap_preview(content, source_id, target_id, extra_class):
    """Generates a preview button and a preview div for given MathContent."""
    # TODO: Implement attachment attribute.
    return {'content': content,
            'source_id': source_id,
            'target_id': target_id,
            'extra_class': extra_class}
