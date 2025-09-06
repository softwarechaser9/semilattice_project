from django import template

register = template.Library()

@register.filter
def to_percentage(value):
    """Convert decimal to percentage (0.5488 -> 54.88)"""
    try:
        return float(value) * 100
    except (ValueError, TypeError):
        return 0

@register.filter
def percentage_width(value):
    """Convert decimal to CSS percentage width (0.5488 -> '54.88%')"""
    try:
        return f"{float(value) * 100:.1f}%"
    except (ValueError, TypeError):
        return "0%"
