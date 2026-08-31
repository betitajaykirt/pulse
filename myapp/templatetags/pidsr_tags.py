from django import template

from myapp.threshold_data import pidsr_category_display

register = template.Library()


@register.filter(name='pidsr_category')
def pidsr_category(disease_label):
    """Return 'Category I' or 'Category II' for a disease name."""
    return pidsr_category_display(disease_label or '')


@register.filter(name='pidsr_category_mod')
def pidsr_category_mod(disease_label):
    label = pidsr_category_display(disease_label or '')
    if label == 'Category I':
        return 'cat1'
    if label == 'Category II':
        return 'cat2'
    return ''


@register.inclusion_tag('partials/pidsr_category_badge.html')
def pidsr_category_badge(disease_label):
    label = pidsr_category_display(disease_label or '')
    return {
        'category': label,
        'mod': 'cat1' if label == 'Category I' else ('cat2' if label == 'Category II' else ''),
    }
