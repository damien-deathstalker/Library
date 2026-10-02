from django.db import models
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
	
	class Meta:
		verbose_name = 'Book'
		verbose_name_plural = 'Books'

class Chapter(models.Model):
	book_fk = models.ForeignKey(Book, on_delete=models.CASCADE, verbose_name='Book')
	title = models.CharField(max_length=150, verbose_name='Chapter Title')
	content = models.TextField()

	def __str__(self):
		return f'{self.title} of {self.book_fk}'

	class Meta:
		verbose_name = 'Book Chapter'
		verbose_name_plural = 'Book Chapters'

class Comment(models.Model):
	chapter_fk = models.ForeignKey(Chapter, on_delete=models.CASCADE, verbose_name='Chapter')
	name = models.CharField(max_length=50, verbose_name='Commenter Name')
	comment_post = models.TextField(verbose_name='Comment')

	def __str__(self):
		return f"{self.name}'s on {self.chapter_fk}"

	class Meta:
		verbose_name = 'Comment'
		verbose_name_plural = 'Comments'