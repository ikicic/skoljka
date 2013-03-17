# helper string functions related to tags

#TODO: prebaciti u string_operations, ili negdje drugdje

# TODO: marksafe
def tag_list_to_html(tags):
    if (type(tags) is str) or (type(tags) is unicode):
        tags = tags.split(',')

    # remove empty tags (e.g. when tags == '')
    tags = [tag.strip() for tag in tags if tag]
    if not tags:
        return u''

    tags.sort()
    return u'[ %s ]' % u' | '.join(
        [u'<a href="/search/?q=%s">%s</a>' % (tag, tag) for tag in tags])
