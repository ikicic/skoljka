# helper string functions related to tags

from utils.string_operations import listStrip

def tagListToHTML(tags):
    if (type(tags) is str) or (type(tags) is unicode):
        tags = tags.split(',')
        
    # remove empty tags (e.g. when tags == '')
    tags = listStrip(tags)
    if not tags:
        return u''
    tags.sort()
    return u'[ %s ]' % u' | '.join( [ "<a href=\"/search/%s/\">%s</a>" % (tag, tag) for tag in tags ] )
