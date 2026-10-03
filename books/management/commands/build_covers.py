"""Build the cover ladder. `python manage.py build_covers`

Run this after adding or replacing a cover, and on deploy. It is idempotent --
a rung that is already current is left alone -- so it costs nothing to run
before every deploy, which is the only way to be sure it is never forgotten.

`--check` asks whether the ladder is there without building any of it, and
exits non-zero if it is not. That is for deploys, where a missing ladder has
no other symptom: every page still renders, because falling back to the
original is a deliberate and silent fallback, so the site is simply 33x heavier
and nothing anywhere says so. Wired into a deploy as a gate, that becomes a
red build instead.
"""

import os

from django.conf import settings
from django.core.management.base import BaseCommand
from PIL import Image

from books.covers import (
	COVER_WIDTHS,
	OK,
	build_variant,
	expected_widths,
	inspect_ladder,
)
from books.models import Book


def label(width):
	return '{}px'.format(width) if width else 'full'


def width_key(width):
	"""Sort rungs narrowest first, with the full-width rung last.

	`None` means the master's own width, so it is both the widest and not a
	number -- comparing it directly against the fixed widths raises.
	"""
	return (width is None, width or 0)


class Command(BaseCommand):
	help = 'Build the smaller WebP versions of every book cover.'

	def add_arguments(self, parser):
		parser.add_argument(
			'--check',
			action='store_true',
			help=('Report covers whose ladder is missing, stale or the wrong '
				'size, and exit non-zero if there are any. Builds nothing.'),
		)

	def handle(self, *args, **options):
		if options['check']:
			# Not named `check`: BaseCommand already has a check() of its own,
			# part of Django's system-check framework, and shadowing it makes
			# this run twice -- once as the framework's hook, once as ours.
			return self.verify()

		return self.build()

	# -- building ----------------------------------------------------------

	def build(self):
		masters = 0
		rows = []

		for book in Book.objects.order_by('pk'):
			if not book.cover_image:
				self.stdout.write('{}: no cover, skipped'.format(book.name))
				continue

			path = book.cover_image.path
			master = os.path.getsize(path)
			masters += master

			built = []
			with Image.open(path) as im:
				# Only the rungs this master can actually have. A rung wider
				# than the master would be an upscale, so it is not built and
				# not counted -- but the full-width rung always is, because it
				# is the master's own pixels.
				for width in expected_widths(im.size[0]):
					built.append((width, build_variant(path, width)))

			rows.append((master, built))

			self.stdout.write('{}: {:.2f} MB -> {} rungs'.format(
				book.name, master / 1048576, len(built)))
			for width, size in built:
				self.stdout.write('    {:>6}  {:>6.0f} KB'.format(
					label(width), size / 1024))

		self.stdout.write('')
		self.stdout.write(self.style.SUCCESS(
			'masters {:.2f} MB. A page fetches one rung per cover:'.format(
				masters / 1048576)))
		for width in COVER_WIDTHS:
			total = sum(
				size for _, built in rows for w, size in built if w == width)
			if total:
				self.stdout.write('    at {:>6}  {:>6.0f} KB for all of them'.format(
					label(width), total / 1024))

	# -- checking ----------------------------------------------------------

	def verify(self):
		books = []
		problems = 0
		per_width = {}

		for book in Book.objects.order_by('pk'):
			if not book.cover_image:
				# Not a fault. A book with no cover has nothing to derive.
				self.stdout.write('{}: no cover, nothing to build'.format(book.name))
				continue

			filename = book.cover_image.name
			master_width, rungs = inspect_ladder(filename)

			if not rungs:
				books.append((book.name, 'no master on disk', []))
				problems += 1
				continue

			if any(r[2] != OK for r in rungs):
				problems += 1

			books.append((book.name, None, rungs))

			# Totals per rung, counting only the rungs that are actually
			# usable. A rung that is missing or stale is not something a page
			# can be served, so counting it would flatter the numbers.
			for width, path, status, _ in rungs:
				if status != OK or not os.path.exists(path):
					continue
				per_width.setdefault(width, [0, 0])
				per_width[width][0] += os.path.getsize(path)
				per_width[width][1] += 1

		for name, note, rungs in books:
			self.stdout.write(name)
			if note:
				self.stdout.write('    {}'.format(note))
				continue
			for width, _path, status, detail in rungs:
				mark = 'ok' if status == OK else status
				self.stdout.write('    {:>6}  {}{}'.format(
					label(width), mark,
					'  ({})'.format(detail) if detail else ''))

		self.stdout.write('')

		masters_total = sum(
			book.cover_image.size for book in Book.objects.order_by('pk')
			if book.cover_image)

		if not books:
			self.stdout.write(self.style.WARNING(
				'no covers to check -- is MEDIA_ROOT populated?'))
			return

		# The headline has to be what a page fetches, which is one rung per
		# cover and not the whole ladder. Summing every rung is the easiest
		# way to make a healthy site look heavy, and a check whose numbers
		# cannot be trusted is a check nobody reads.
		#
		# The shelf asks for `sizes="153px"`, so it takes the 160 rung at 1x
		# and the 320 at 2x. The 320 is quoted as the headline because it is
		# the worse of the two and the one any current screen will pick.
		headline = 320 if 320 in per_width else max(per_width, default=None, key=width_key)
		if headline is not None:
			served, _count = per_width[headline]
			self.stdout.write(
				'masters {:.2f} MB. The shelf fetches the {} rung: {:.0f} KB.'.format(
					masters_total / 1048576, label(headline), served / 1024))
		else:
			served = 0

		other = sorted((w for w in per_width if w != headline), key=width_key)
		if other:
			self.stdout.write('    every rung, for the other pages that ask wider:')
			for width in other:
				total, count = per_width[width]
				self.stdout.write('        {:>6}  {:>6.0f} KB across {} covers'.format(
					label(width), total / 1024, count))

		if problems:
			# On stderr, not just coloured. `self.style.ERROR` only adds ANSI
			# colour -- it does not choose a stream -- so writing it to stdout
			# would leave a deploy log full of failure text on the same channel
			# as the per-rung table it is reporting on. This command exists to
			# be a gate, and a gate that fails quietly in a wall of output is
			# a gate people stop reading.
			self.stderr.write('')
			self.stderr.write(self.style.ERROR(
				'{} of {} covers are not fully built. Nothing will say so at '
				'runtime -- the pages fall back to the original and render '
				'perfectly -- so the shelf is quietly {:.2f} MB heavier than it '
				'needs to be.'.format(problems, len(books), masters_total / 1048576)))
			self.stderr.write(self.style.ERROR('  fix: python manage.py build_covers'))
			raise SystemExit(1)

		self.stdout.write('')
		self.stdout.write(self.style.SUCCESS(
			'every cover is built. {:.0f} KB on the shelf instead of {:.2f} '
			'MB of originals.'.format(served / 1024, masters_total / 1048576)))
