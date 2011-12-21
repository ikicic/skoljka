# helper string functions related to tags

from utils.string_operations import list_strip

#TODO: prebaciti u string_operations, ili negdje drugdje

# TODO: marksafe
def tag_list_to_html(tags):
    if (type(tags) is str) or (type(tags) is unicode):
        tags = tags.split(',')
        
    # remove empty tags (e.g. when tags == '')
    tags = list_strip(tags)
    if not tags:
        return u''
    tags.sort()
    return u'[ %s ]' % u' | '.join( [ u'<a href="/search/?q=%s">%s</a>' % (tag, tag) for tag in tags ] )
