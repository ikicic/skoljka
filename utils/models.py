from django.template.loader import add_to_builtins


# ovo navodno nije preporuceno, ali vjerujem da ce se
# dovoljno cesto koristiti da DRY nadjaca
add_to_builtins('utils.templatetags.utils_tags')
