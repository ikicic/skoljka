# useful string operations

def list_strip(L, remove_empty=True):
    T = [x.strip() for x in L]
    if remove_empty:
        return filter(None, T)
    return T