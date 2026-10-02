from django.db.models import Count
from django.shortcuts import render

from books.models import Book

# Create your views here.
def index(request):
	# chapter_count powers the label under each cover on the shelf, so the
	# shelf reports the length of a book before you commit to opening it.
	context = dict(
		books = Book.objects.annotate(chapter_count=Count('chapter')).order_by('id')
	)
	return render(request, "shelf/index.html", context)