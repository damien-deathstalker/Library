import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()

BLANK_LINE = re.compile(r'\n[ \t]*\n')
NEWLINE = re.compile(r'\n+')


def split_paragraphs(value):
	"""Break text into its paragraphs.

	Blank lines separate paragraphs. Text is hard-wrapped in the database for
	readability in the admin, so line breaks inside a paragraph are rejoined
	with spaces rather than kept — otherwise the prose renders ragged and never
	picks up justification.
	"""
	text = (value or '').strip()
	if not text:
		return []

	blocks = [b.strip() for b in BLANK_LINE.split(text)]
	blocks = [b for b in blocks if b]

	# No blank lines anywhere: each line is its own paragraph.
	if len(blocks) == 1 and '\n' in blocks[0]:
		blocks = [b.strip() for b in blocks[0].split('\n') if b.strip()]

	return [NEWLINE.sub(' ', b).strip() for b in blocks]


@register.filter(name='paragraphs', is_safe=True)
def paragraphs(value):
	"""Render chapter text as real <p> blocks."""
	return mark_safe(
		''.join('<p>%s</p>' % escape(b) for b in split_paragraphs(value))
	)