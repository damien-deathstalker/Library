$("#Decrease").click(function () {
	if (font_size > 0.5) {
		font_size = parseFloat(font_size) - 0.1;
		change_font(font_size);
	}
})
$("#Default").click(function () {
	font_size = 1;
	change_font(parseFloat(font_size));
})
$("#Increase").click(function () {
	font_size = parseFloat(font_size) + 0.1;
	change_font(font_size);
})
function change_font(size) {
	set_cookie("fontsize", size, style_cookie_duration, style_domain);
	$('#chapter_content').css("font-size", size + "em");
}
var font_size = 1;
$(document).ready(function () {
	var cookie_font_size = get_cookie('fontsize');
	if (cookie_font_size != "") {
		font_size = cookie_font_size;
		$('#chapter_content').css("font-size", cookie_font_size + "em");
		$("#name").val(get_cookie("user_name"));
	}
})
$("#submitBtn").click(function (e) {
	e.preventDefault();
	var name = $("#name").val();
	var comment = $("#comment").val();
	if (name.length > 3 && comment.length > 4) {
		$.ajax({
			url: comment_post_url,
			method: "POST",
			data: {
				name: name,
				comment: comment,
				csrfmiddlewaretoken: $('input[name=csrfmiddlewaretoken]').val(),
			},
			success: function (data) {
				set_cookie("user_name", name, style_cookie_duration, style_domain);
				loadComments();
				$("#comment").val("");
			}
		})
	} else {
		swal('Hold On!', 'Either the name or the comment is too short', 'warning');
	}
})
function loadComments() {
	$.get(load_comments_url, function (data) {
		$("#commentsDiv").html(data.html);
	})
}
