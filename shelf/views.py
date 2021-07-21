from django.shortcuts import render
from books.models import Book
# Create your views here.
def index(request):
	context = dict(
		books = Book.objects.all()
	)
	return render(request, "shelf/index.html", context)