from django.db import models
from django.utils.safestring import mark_safe

# Create your models here.
class Book(models.Model):
	name = models.CharField(max_length=150)
	blurb = models.TextField(max_length=500)
	cover_image = models.ImageField(upload_to='cover_images')

	def __str__(self):
		return self.name

	def get_chapters(self):
		return Chapter.objects.filter(book_fk=self)
	
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
	book_fk = models.ForeignKey(Book, on_delete=models.CASCADE)
	title = models.CharField(max_length=150)
	content = models.TextField()

	def __str__(self):
		return f'{self.title} of {self.book_fk}'

	class Meta:
		verbose_name = 'Book Chapter'
		verbose_name_plural = 'Book Chapters'

class Comment(models.Model):
	chapter_fk = models.ForeignKey(Chapter, on_delete=models.CASCADE)
	name = models.CharField(max_length=50)
	comment_post = models.TextField()

	class Meta:
		verbose_name = 'Comment'
		verbose_name_plural = 'Comments'