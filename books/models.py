from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.utils.safestring import mark_safe

# Fonts a story can ask to be set in. The admin field is free text, so it is
# resolved against this map rather than dropped straight into a style
# attribute. Anything unrecognised falls back to the reading serif.
FONT_STACKS = {
	'times new roman': "'Times New Roman', Times, serif",
	'times': "'Times New Roman', Times, serif",
	'serif': "'Times New Roman', Times, serif",
	'georgia': "Georgia, 'Times New Roman', serif",
	'bookman': "'Bookman Old Style', Georgia, serif",
	'palatino': "'Palatino Linotype', 'Book Antiqua', Georgia, serif",
	'garamond': "Garamond, Georgia, serif",
	'baskerville': "Baskerville, Georgia, serif",
	'constantia': "Constantia, Cambria, Georgia, serif",
	'cambria': "Cambria, Georgia, serif",
	'caslon': "Caslon, Georgia, serif",
	'didot': "Didot, 'Bodoni MT', Georgia, serif",
	'courier new': "'Courier New', Courier, monospace",
	'courier': "'Courier New', Courier, monospace",
	'monospace': "'Courier New', Courier, monospace",
	'consolas': "Consolas, 'Courier New', monospace",
	'menlo': "Menlo, Consolas, monospace",
	'arial': "Arial, Helvetica, sans-serif",
	'helvetica': "Helvetica, Arial, sans-serif",
	'verdana': "Verdana, Arial, sans-serif",
	'tahoma': "Tahoma, Arial, sans-serif",
	'calibri': "Calibri, Arial, sans-serif",
	'sans-serif': "'Archivo', system-ui, sans-serif",
	'sans serif': "'Archivo', system-ui, sans-serif",
	'futura': "Futura, 'Century Gothic', sans-serif",
	'century gothic': "'Century Gothic', Futura, sans-serif",
	'gill sans': "'Gill Sans', 'Gill Sans MT', sans-serif",
	'optima': "Optima, Candara, sans-serif",
	'trebuchet ms': "'Trebuchet MS', Arial, sans-serif",
	'impact': "Impact, 'Arial Black', sans-serif",
	'brush script mt': "'Brush Script MT', cursive",
	'comic sans ms': "'Comic Sans MS', cursive",
	'cursive': "'Segoe Script', 'Brush Script MT', cursive",
}

DEFAULT_READING_STACK = "'Newsreader', Georgia, 'Times New Roman', serif"

# Create your models here.
class Book(models.Model):
	name = models.CharField(max_length=150, verbose_name='Book Name')
	blurb = models.TextField(max_length=500, verbose_name='Book Description')
	cover_image = models.ImageField(upload_to='cover_images', verbose_name='Book Cover')
	font = models.CharField(max_length=50, verbose_name='Book Font', default='Times New Roman')

	def __str__(self):
		return self.name

	@property
	def font_stack(self):
		"""A safe CSS font-family for this book's prose."""
		key = (self.font or '').strip().lower().strip('\'"')
		return FONT_STACKS.get(key, DEFAULT_READING_STACK)

	def get_chapters(self):
		return Chapter.objects.filter(book_fk=self).order_by('pk')

	def get_cover_image(self, **kwargs):
		height = kwargs.get('height', None)
		width = kwargs.get('width', None)
		if not all([height, width]):
			height = 150
			width = 150
		return mark_safe(f'<img style="max-width: {width}px; max-height: {height}px;" src="/media/{self.cover_image}/">')

	# There is deliberately no `is_complete` property here. A property is a
	# data descriptor, so it outranks the instance dict and would shadow an
	# annotation of the same name: a queryset could annotate `is_complete`,
	# get the answer it asked for, and still be issuing one query per book.
	# Asking is cheap to spell and impossible to get wrong that way, so the
	# shelf and the admin both annotate this and neither asks.

	class Meta:
		verbose_name = 'Book'
		verbose_name_plural = 'Books'

class Chapter(models.Model):
	book_fk = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='Book')
	title = models.CharField(max_length=150, verbose_name='Chapter Title')
	content = models.TextField()
	# The end of the story. Marking one closes the book: it stops appearing as
	# ongoing, and no further chapter can be added until this comes off again.
	is_final = models.BooleanField(default=False, verbose_name='Last chapter of the book')

	def __str__(self):
		return f'{self.title} of {self.book_fk}'

	def clean(self):
		"""Three rules about ending a book, all of them about the book.

		They live here rather than in the admin so they hold however the chapter
		is written -- admin form, shell, fixture -- and `clean` is the one place
		ModelForm calls on save, so the admin reports them as messages on the
		form rather than as a traceback.
		"""
		# Whatever else this chapter is, the book may already have an ending.
		# Ours is not that one if we are not the chapter being saved.
		settled = Chapter.objects.filter(book_fk_id=self.book_fk_id, is_final=True)
		if self.pk:
			settled = settled.exclude(pk=self.pk)
		end = settled.first()

		if self.is_final:
			if end is not None:
				raise ValidationError(
					f'“{end.title}” is already the last chapter of this book. Only one '
					'chapter can be the last.',
					code='already_settled',
				)
			# A chapter marked as the last with chapters written after it would
			# mean the book ends twice. Chapters are read in id order, so those
			# are the ones above this one's id. A chapter being created has none
			# written after it yet.
			if self.pk:
				later = Chapter.objects.filter(book_fk_id=self.book_fk_id, pk__gt=self.pk).count()
				if later:
					raise ValidationError(
						'This cannot be the last chapter: {} chapter{} {} it. Take {} off '
						'first, or mark the one you actually finished with.'
						.format(
							later,
							'' if later == 1 else 's',
							'follows' if later == 1 else 'follow',
							'it' if later == 1 else 'them',
						),
						code='not_the_last',
					)
		elif self.pk is None and end is not None:
			raise ValidationError(
				f'This book ended at “{end.title}”, so it cannot take another chapter. '
				'Unmark that one first if the story has reopened.',
				code='book_settled',
			)

	class Meta:
		verbose_name = 'Book Chapter'
		verbose_name_plural = 'Book Chapters'
		constraints = [
			# The rule the admin can be raced past: two admin tabs open on the
			# same book both pass clean(), so the database has to be the one
			# holding the line. Only rows that are endings take part, so a book
			# can have any number of chapters that are not the last one.
			models.UniqueConstraint(
				fields=['book_fk'],
				condition=Q(is_final=True),
				name='one_last_chapter_per_book',
			),
		]

class Comment(models.Model):
	chapter_fk = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name='Chapter')
	name = models.CharField(max_length=50, verbose_name='Commenter Name')
	comment_post = models.TextField(verbose_name='Comment')

	def __str__(self):
		return f"{self.name}'s on {self.chapter_fk}"

	class Meta:
		verbose_name = 'Comment'
		verbose_name_plural = 'Comments'