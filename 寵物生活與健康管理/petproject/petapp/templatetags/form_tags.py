from django import template

register = template.Library()

@register.filter(name='add_class')
def add_class(field, css_class):
    return field.as_widget(attrs={"class": css_class})

@register.filter(name='add_error_class')
def add_error_class(field):
    css_class = "form-control"
    if field.errors:
        css_class += " is-invalid"
    return field.as_widget(attrs={"class": css_class})