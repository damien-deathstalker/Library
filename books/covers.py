"""Covers, at the sizes they are actually painted.

The shelf is a shelf, not a gallery. A cover is never shown larger than the
slot it sits in, which is 244px tall and five-eighths as wide -- 152 CSS
pixels -- and the card that lifts off the board shows it in the same 152. The
book page shows it in a 13rem column, or full-bleed on a phone.

None of that is anywhere near the 1410x2250 the originals are stored at, so
every page was asking for a file four to nine times the size of the thing it
was drawing. Four covers came to 7.7 MB, and 5.9 MB of that was one book:
`i_wrote_this_the_morning_after.png` is a flat PNG of a gradient, which is
close to the worst thing you can hand a browser.

So the originals are kept exactly as they were uploaded -- that is the master,
and the book page's own image and the admin's thumbnail still point at it -- and
a ladder of smaller WebP files is built alongside. A ladder rather than one
size because the covers are painted at three quite different widths (the slot,
the card, and a phone-width book page), and because a 1x screen should not pay
for a 2x one.

Nothing here runs during a request. `srcset` only ever names files that a build
step has already written; if they are missing it falls back to the original, so
a fresh checkout renders correctly before anyone thinks to run the command.
"""

import os

from django.conf import settings
from PIL import Image

# The widths a cover is built at. Chosen from the measurements in
# `src/css/shelf.css` and `src/css/reader.css`:
#
#   160  the shelf slot and the card at 1x
#   320  the shelf slot and the card at 2x
#   640  a book page on a desktop at 2x (208 CSS px column)
#  1280  a book page on a phone at 2x, where the cover goes full-bleed
#
# And then the master's own width, which is the one case a ladder of round
# numbers misses: a book page between 44rem and about 48rem lays the cover out
# 660 CSS px wide, and a 2x screen there wants 1320 -- more than 1280 covers.
# Falling through to the original for that is 1.01 MB of PNG for Parallel and
# 5.93 MB for the morning-after book, where the same pixels as WebP are 88 KB
# and 800 KB. None rather than 1410, because masters differ in width and this
# should ask each one for its own rather than assume.
COVER_WIDTHS = (160, 320, 640, 1280, None)

# WebP at 82 with a decent encode effort. Covers are flat gradients and
# lettering: the banding that shows up in smooth gradients is the thing to
# watch, and 82 with method 6 keeps it out while still landing the whole
# ladder under 130 KB. Higher settings buy invisible kilobytes here.
COVER_QUALITY = 82
COVER_METHOD = 6

# Where the derived files go. A sibling directory rather than alongside the
# original, so that a glance at `media/cover_images/` still shows what has
# actually been uploaded and nothing else.
COVER_DIR = 'cover_images/_sized'


def sized_name(filename, width, suffix='webp'):
	"""The derived filename for one rung of the ladder.

	`parallel.png` at 640 becomes `parallel-640.webp`. The width is in the name
	so a rebuilt ladder replaces its files instead of accumulating beside them.
	"""
	stem, _ext = os.path.splitext(os.path.basename(filename))
	return '{}-{}.{}'.format(stem, width if width else 'full', suffix)


def variant_path(filename, width):
	"""Where one rung lives, absolute."""
	return os.path.join(settings.MEDIA_ROOT, COVER_DIR, sized_name(filename, width))


def master_path(filename):
	"""Where the original lives, absolute."""
	return os.path.join(settings.MEDIA_ROOT, filename)


def expected_widths(master_width):
	"""The rungs a master this wide should have on disk.

	The one place the answer lives, so that building and checking cannot come to
	disagree about what "done" means -- a check that asked a second, slightly
	different question would either miss rungs or demand ones that were never
	meant to exist.

	A rung wider than the master is dropped rather than the ladder stopping
	there: the widest rung is the master's own width, so it is always buildable,
	and a cover narrower than the smallest rung should still get re-encoded
	rather than be left as the only PNG on the site.
	"""
	return [w for w in COVER_WIDTHS if w is None or w <= master_width]


def build_variant(source_path, width):
	"""Write one rung of the ladder. Returns its size in bytes.

	`width=None` is the widest rung: the master's own pixels, re-encoded. It is
	the one rung that is never resized, and the reason is the encoding rather
	than the size -- the originals are PNG, and a PNG of a flat gradient is
	several times larger than the same picture as WebP.

	Every cover is stored as RGBA PNG with a fully opaque alpha channel, so the
	channel is dropped on the way through: WebP would carry the alpha, and
	carrying an alpha that is opaque everywhere costs bytes and buys nothing.

	Upscaling is refused. A rung wider than the master is a mistake, and
	producing one would make a blurry cover look deliberate.

	A rung older than its master is rewritten rather than kept. Replacing a
	cover keeps its filename, so the rungs beside it would otherwise go on
	serving the artwork that was there before -- the exact kind of quiet wrong
	that nothing else would notice.
	"""
	target = variant_path(os.path.relpath(source_path, settings.MEDIA_ROOT), width)
	if os.path.exists(target) and not is_stale(target, source_path):
		return os.path.getsize(target)

	with Image.open(source_path) as im:
		master_width = im.size[0]

		if width is None:
			# The widest rung needs no resampling at all, so it skips the
			# Lanczos pass entirely: re-encoding a full-size image through a
			# resampler only softens it.
			out = im.convert('RGB')
		else:
			if width > master_width:
				raise ValueError(
					'{} is only {} wide, so a {}-wide version would be an '
					'upscale.'.format(os.path.basename(source_path), master_width, width)
				)
			height = round(im.size[1] * width / master_width)
			out = im.convert('RGB').resize((width, height), Image.LANCZOS)

		os.makedirs(os.path.dirname(target), exist_ok=True)
		out.save(target, 'WEBP', quality=COVER_QUALITY, method=COVER_METHOD)
		out.close()

	return os.path.getsize(target)


def srcset_for(filename):
	"""A `srcset` for the rungs that exist, widest last.

	Falls back to the original alone when the ladder has not been built, so the
	markup is always usable. The original is offered as the widest candidate on
	top of the ladder rather than instead of it: it is the master, and a screen
	tall enough to want more than 1280 should have the real pixels rather than
	an upscaled guess.
	"""
	base = settings.MEDIA_URL

	parts = []
	for width in COVER_WIDTHS:
		if os.path.exists(variant_path(filename, width)):
			# MEDIA_URL on its own, not the field's .url: the field's url is
			# absolute-path off the storage, and joining the two would repeat
			# the upload directory -- /media/cover_images/parallelpng.
			url = '{}{}/{}'.format(base, COVER_DIR, sized_name(filename, width))
			descriptor = im_width(filename) if width is None else width
			parts.append('{} {}w'.format(url, descriptor))

	if not parts:
		return None

	# The original stays as the last resort, for a master whose widest rung was
	# never built. It is never reached once `build_covers` has run, because the
	# full-width rung is always available and always smaller.
	master = im_width(filename)
	if master and not parts[-1].endswith(' {}w'.format(master)):
		parts.append('{}{} {}w'.format(base, filename, master))

	return ', '.join(parts)


def im_width(filename):
	"""The master's own width, for the `w` descriptor on the fallback."""
	path = master_path(filename)
	if not os.path.exists(path):
		return 0
	with Image.open(path) as im:
		return im.size[0]


def is_stale(rung, master):
	"""Whether a rung was built from an older version of its master.

	By modification time, which is the only cheap signal available: the ladder's
	filenames carry the width but not a hash of the picture, so nothing on disk
	records which master a rung came from.

	That makes this a heuristic, and it is worth being honest about the one way
	it can mislead. A fresh `git clone` stamps every file with the checkout
	time, so a master and a rung restored together can land either way round
	and a rung can read as stale when it is not. The cost of that is one
	redundant re-encode; the cost of trusting the other direction is serving
	the old cover indefinitely.
	"""
	try:
		return os.path.getmtime(rung) < os.path.getmtime(master)
	except OSError:
		return False


# What a rung can be other than fine. Kept as constants because the command
# writes them into its output and the check compares against them.
MISSING = 'missing'
STALE = 'stale'
WRONG_SIZE = 'wrong size'
OK = 'ok'


def inspect_ladder(filename):
	"""What is on disk for one cover, against what should be.

	Returns `(master_width, rungs)` where each rung is
	`(width, path, status, detail)`. A rung that is not on disk still appears,
	with a status, so the report can show the whole shape of the ladder rather
	than only its holes.

	Four things can be wrong, and all four are worth catching:

	  missing     never built -- the server fell back to the original, which
	              renders perfectly and is 33x heavier
	  stale       built before the master was last changed
	  wrong size  on disk but not the width its filename claims, which means a
	              half-written file or a master replaced at a different size
	  unreadable  present but not an image Pillow can open
	"""
	master = master_path(filename)
	if not os.path.exists(master):
		return 0, []

	with Image.open(master) as im:
		master_width = im.size[0]

	rungs = []
	for width in expected_widths(master_width):
		path = variant_path(filename, width)
		expected = master_width if width is None else width

		if not os.path.exists(path):
			rungs.append((width, path, MISSING, 'never built'))
			continue

		if is_stale(path, master):
			rungs.append((width, path, STALE, 'older than its master'))
			continue

		try:
			with Image.open(path) as im:
				actual = im.size[0]
		except Exception as exc:  # a truncated or non-image file
			rungs.append((width, path, WRONG_SIZE, str(exc)))
			continue

		if actual != expected:
			rungs.append((width, path, WRONG_SIZE,
				'{}px wide, named for {}'.format(actual, expected)))
			continue

		rungs.append((width, path, OK, ''))

	return master_width, rungs