import copy

# TODO(gzuzic): research for a generic replacement?
# TODO(gzuzic): make a prefix for different forms so no clashing occurs
class ModelFormList(object):
    """
    A ``ModelFormList`` is a class that aggregates a list of forms.
    It's API is supposed to mimic ModelForm as far as possible with
    a caveat that it doesn't wont to talk directly with the db via save().

    You should create it only by the formlist_factory method.
    """
    def __init__(self, values = None):
        self.forms = []
        for form in self.FORMS:
            self.forms.append(form(values))

    def __iter__(self):
        return self.forms.__iter__()

    def is_valid(self):
        self.cleaned_data = dict()
        for form in self.forms:
            if not form.is_valid():
                return False
            self.cleaned_data.update(form.cleaned_data)
        return True

    def save(self, commit=True):
        if commit:
            # Commiting to the db is tricky because of order dependacies
            # and can lead to subtle errors. It's better to delegate it
            # to the caller to handle
            raise NotImplementedError("Generic ModelFormList shouldn't commit to db")
        return [ form.save(commit=commit) for form in self.forms ]

def modelformlist_factory(*args):
    """
    Constructs a ModelFormList that aggregates the classess passed
    though the arguments.
    
    Example:
        TaskModelFormList = modelformlist_factory(Task1Form, AuthorForm);
    """
    CloneModelFormList = copy.copy(ModelFormList)
    CloneModelFormList.FORMs = args
    return CloneModelFormList
