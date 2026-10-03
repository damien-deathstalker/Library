from django.db.models import Count, Exists, OuterRef, Subquery
from django.shortcuts import render

from books.models import Book, Chapter

# Create your views here.
def index(request):
	# Three questions the shelf asks about every book, all answered here rather
	# than in the template, so a shelf of titles costs the same however many
	# titles are standing on it.
	#
	#   chapter_count    how long it is, said under the cover before you commit
	#   is_complete      whether it has an ending, which is what the filter
	#                    divides the shelf on
	#   last_chapter_id  which chapter ends it, so a reader who has arrived
	#                    there is told they finished rather than handed a
	#                    "continue" link to the thing they have already read
	#
	# The shelf is one board. Whether a book is going or completed is a filter
	# over it rather than a second shelf, because the two groups are the same
	# thing seen two ways -- a reader choosing what to read cares about the
	# cover and the title, not which side of a divide it came from.
	return render(request, 'shelf/index.html', {
		'books': Book.objects.annotate(
			chapter_count=Count('chapter'),
			is_complete=Exists(
				Chapter.objects.filter(book_fk=OuterRef('pk'), is_final=True)
			),
			last_chapter_id=Subquery(
				Chapter.objects.filter(book_fk=OuterRef('pk'), is_final=True).values('pk')[:1]
			),
		).order_by('id'),
	})