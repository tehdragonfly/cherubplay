$(".delete_form").submit(function() {
	var confirm_end = confirm("Are you sure you want to delete this chat? This cannot be undone.");
	if (confirm_end) {
		$.post(this.action);
		this.parentNode.remove();
	}
	return false;
});
