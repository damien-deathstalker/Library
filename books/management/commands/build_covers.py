"""Build the cover ladder. `python manage.py build_covers`

Run this after adding or replacing a cover, and on deploy. It is idempotent --
a rung that is already on disk is left alone -- so it costs nothing to run
before every deploy, which is the only way to be sure it is never forgotten.
"""

import os

from django.core.management.base import BaseCommand

from books.covers import COVER_WIDTHS, build_variant
from books.models import Book


def label(width):
	return '{}px'.format(width) if width else 'full'


class Command(BaseCommand):
	help = 'Build the smaller WebP versions of every book cover.'

	def handle(self, *args, **options):
		masters = 0
		rows = []

		for book in Book.objects.order_by('pk'):
			if not book.cover_image:
				self.stdout.write('{}: no cover, skipped'.format(book.name))
				continue

			path = book.cover_image.path
			master = os.path.getsize(path)
			masters += master

			written = []
			# A master narrower than a rung stops the ladder there rather than
			# producing an upscale. The widest rung is the master's own width,
			# so this only bites on an unusually small cover.
			for width in COVER_WIDTHS:
				try:
					written.append((width, build_variant(path, width)))
				except ValueError as exc:
					self.stdout.write('  {}: {}'.format(book.name, exc))
					break

			rows.append((master, written))

			self.stdout.write('{}: {:.2f} MB -> {} rungs'.format(
				book.name, master / 1048576, len(written)))
			for width, size in written:
				self.stdout.write('    {:>6}  {:>6.0f} KB'.format(
					label(width), size / 1024))

		self.stdout.write('')
		self.stdout.write(self.style.SUCCESS(
			'masters {:.2f} MB. A page fetches one rung per cover:'.format(
				masters / 1048576)))
		for width in COVER_WIDTHS:
			total = sum(
				size for _, written in rows for w, size in written if w == width)
			if total:
				self.stdout.write('    at {:>6}  {:>6.0f} KB for all of them'.format(
					label(width), total / 1024))