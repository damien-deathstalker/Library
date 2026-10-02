from django.http.response import JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string

from books.models import Book, Chapter, Comment


# Create your views here.
def book_index(request, book_id):
	book = get_object_or_404(Book, pk=book_id)
	return render(request, 'reader/index.html', {
		'book': book,
		'chapters': book.get_chapters(),
	})


def read_chapter(request, book_id, chapter_id):
	chapter = get_object_or_404(Chapter, pk=chapter_id, book_fk__id=book_id)
	chapters = list(Chapter.objects.filter(book_fk__id=book_id).order_by('pk'))
	index = chapters.index(chapter)

	context = {
		'book': chapter.book_fk,
		'chapter': chapter,
		'chapters': chapters,
		'chapter_number': index + 1,
		'comments': Comment.objects.filter(chapter_fk=chapter),
	}
	if index > 0:
		context['previous_chapter'] = chapters[index - 1]
	if index < len(chapters) - 1:
		context['next_chapter'] = chapters[index + 1]

	return render(request, 'reader/read.html', context)


def chapter_comments(request, chapter_id):
	"""List comments for a chapter, or post one.

	Always answers with JSON: {'html': ...} for a rendered fragment, or
	{'error': ...} with a 400. Replaces the old request.is_ajax() check,
	which Django removed in 4.0.
	"""
	chapter = get_object_or_404(Chapter, pk=chapter_id)

	if request.method == 'POST':
		name = (request.POST.get('name') or '').strip()
		body = (request.POST.get('comment') or '').strip()

		if len(name) < 2:
			return JsonResponse({'error': 'Add your name so I know who is reading.'}, status=400)
		if len(body) < 5:
			return JsonResponse({'error': 'Write a little more than that.'}, status=400)

		Comment.objects.create(
			chapter_fk=chapter,
			name=name[:50],
			comment_post=body,
		)
	elif request.method != 'GET':
		return JsonResponse({'error': 'Method not allowed.'}, status=405)

	comments = Comment.objects.filter(chapter_fk=chapter)
	return JsonResponse({
		'html': render_to_string('reader/comments.html', {'comments': comments}),
		'count': comments.count(),
	})