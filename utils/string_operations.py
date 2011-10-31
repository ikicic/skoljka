# useful string operations

def listStrip(L, removeEmpty=True):
    T = [x.strip() for x in L]
    if removeEmpty:
        T = filter(None, T)
    return T