from django import template
from django.conf import settings
from django.utils.html import mark_safe

from skoljka.mathcontent.utils import convert_to_html

register = template.Library()


@register.inclusion_tag('inc_mathcontent_render.html')
def mathcontent_render(content, quote=False):
    if content.html is None:
        try:
            content.html = convert_to_html(content.text, content=content)
        except Exception:
            if getattr(settings, 'MATHCONTENT_DEBUG', False):
                raise
            # Leave content.html as None. If None, template will notify the
            # user about the error. No error details are provided.
            pass
        else:
            content._no_html_reset = True
            content.save()

    return {
        'content': content,
        # 'view_source': request.user.is_authenticated(),
        'view_source': True,
        'quote': quote,
    }


@register.simple_tag
def mathcontent_render_quote(content):
    return mathcontent_render(content, quote=True)


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
    return {
        'content': content,
        'source_id': source_id,
        'target_id': target_id,
        'extra_class': extra_class,
    }
