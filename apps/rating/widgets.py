from django.forms.widgets import Widget, RadioSelect
from django.utils.safestring import mark_safe

class RatingWidget(RadioSelect):
    def __init__(self, attrs):
        attrs['choices'] = zip(range(attrs['range']), attrs['titles'])
        super(RadioSelect, self).__init__(attrs)
        
    def render(self, name, value, attrs=None):
        A = self.attrs
        split = '' if A['range'] == 5 else ' {split:%d}' % (A['range'] / 5)
        value = 0 if value is None else int(value)
        
        stars = [
            u'<input name="%(name)s" type="radio" class="star%(split)s" value="%(value)s" title="%(title)s"%(checked)s>' % {
                'name': name,
                'split': split,
                'value': x+1,
                'title': A['titles'][x],
                'checked': ' checked="checked"' if x+1 == value else '',
            } for x in range(1, A['range'])]
        return mark_safe(u'<div>%s</div>' % ''.join(stars))
