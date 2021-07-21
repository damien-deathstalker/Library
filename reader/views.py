from django.http.response import Http404, JsonResponse
from books.models import Book, Chapter, Comment
from django.shortcuts import render
from django.template.loader import render_to_string


# Create your views here.
def book_index(request, book_id):
	context = dict(
		book = Book.objects.get(pk=book_id)
	)
	return render(request, 'reader/index.html', context)

def read_chapter(request, book_id, chapter_id):
	context = dict(
		chapter = Chapter.objects.get(id=chapter_id, book_fk__id=book_id),
		comments = Comment.objects.filter(chapter_fk__id=chapter_id)
	)
	book_chapters = Chapter.objects.filter(book_fk__id=book_id).order_by('pk')
	chapter_list = list(book_chapters)
	if book_chapters.first() != context['chapter']:
		context.update(
			previous_chapter = chapter_list[chapter_list.index(context['chapter'])-1]
		)
	if book_chapters.last() != context['chapter']:
		context.update(
			next_chapter = chapter_list[chapter_list.index(context['chapter'])+1]
		)
	return render(request, 'reader/read.html', context)

def chapter_comments(request, chapter_id):
	if request.is_ajax():
		if request.method == "POST":
			name = request.POST.get('name', None)
			comment_post = request.POST.get('comment', None)
			if all([name, comment_post]):
				new_comment = Comment(
					chapter_fk = Chapter.objects.get(id=chapter_id),
					name = name, comment_post = comment_post
				)
				new_comment.save()
		context = dict(
			comments=Comment.objects.filter(chapter_fk__id=chapter_id)
		)
		return JsonResponse(dict(html=render_to_string('reader/comments.html', context)))
	raise Http404