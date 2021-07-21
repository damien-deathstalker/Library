from django.db import models
from django.db.models.base import Model

# Create your models here.
class Book(models.Model):
	name = models.CharField(max_length=150)
	blurb = models.TextField(max_length=500)
	cover_image = models.ImageField(upload_to='cover_images')

	def __str__(self):
		return self.name

	def get_chapters(self):
		return Chapter.objects.filter(book_fk=self)

class Chapter(models.Model):
	book_fk = models.ForeignKey(Book, on_delete=models.CASCADE)
	title = models.CharField(max_length=150)
	content = models.TextField()

	def __str__(self):
		return f'{self.title} of {self.book_fk}'

class Comment(models.Model):
	chapter_fk = models.ForeignKey(Chapter, on_delete=models.CASCADE)
	name = models.CharField(max_length=50)
	comment_post = models.TextField()