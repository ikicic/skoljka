from django import forms


class NonStickyTextInput(forms.TextInput):
    """Custom text input that does not show the entered value when a form validation fails."""

    def render(self, name, value, attrs):
        # From the implementation of PasswordInput.
        value = None
        return super(NonStickyTextInput, self).render(name, value, attrs)
