
var colour_regex = /^#[0-9a-f]{6}$/i;
var typing = false;
var typing_timeout;
var ended = false;
var continue_timeout;

function is_at_bottom() {
	return window.scrollY==document.documentElement.scrollHeight-document.documentElement.clientHeight;
}

function scroll_to_bottom() {
	window.scroll(0, document.documentElement.scrollHeight-document.documentElement.clientHeight);
}

function visibility_handler() {
	window.setTimeout(function() {
		document.title = "CHERUBPLAY";
	}, 200);
}

var messages = $("#messages");
var status_bar = $("#status_bar");
var last_status_message = status_bar.text();
var message_form_container = $("#message_form_container");
var message_form = $("#message_form").submit(function() {
	typing = false;
	window.clearTimeout(typing_timeout);
	if (!colour_regex.test(message_colour.val())) {
		alert("The colour needs to be a valid hex code, for example \"#0715CD\" or \"#416600\".");
		return false;
	}
	message_text.val(message_text.val().trim());
	if (message_text.val()=="") {
		alert("You can't submit a blank message.")
		return false;
	}
	if (ws.readyState==1) {
		$.ajax({
			"url": this.action,
			"method": "POST",
			"data": message_form.serializeArray(),
			"success": function() {
				message_text.val("").css("height", "100px");
			},
			"error": function() {
				alert("There was an error with your message. Please try again later.");
			},
			"complete": function() {
				message_colour.removeAttr("disabled");
				message_text.removeAttr("disabled");
			},
		});
		message_colour.attr("disabled", "disabled");
		message_text.attr("disabled", "disabled");
		return false;
	}
});
var message_colour = $("#message_colour").change(function() {
	message_text.css("color", this.value);
});
var preset_colours = $("#preset_colours").change(function() {
	message_colour.val(this.value).change();
});
var message_text = $("#message_text").keypress(function(e) {
	if (e.keyCode==13 && !e.shiftKey) {
		message_form.submit();
		return false;
	} else if (ws.readyState==1) {
		window.clearTimeout(typing_timeout);
		if (!typing) {
			typing = true;
			ws.send("{\"action\":\"typing\"}");
		}
		typing_timeout = window.setTimeout(function() {
			typing = false;
			ws.send("{\"action\":\"stopped_typing\"}");
		}, 1000);
	}
}).keyup(function(e) {
	// Check if we're at the bottom before resizing because resizing will mean that we're not.
	var scroll_after_resize = is_at_bottom();
	this.style.height = this.scrollHeight+"px";
	if (scroll_after_resize) {
		scroll_to_bottom();
	}
});
var end_form = $("#end_form").submit(function() {
	var confirm_end = confirm("Are you sure you want to end this chat? Once a chat has ended you can't continue it later. If you'd like to continue this chat later, please click cancel and then close this window/tab.");
	if (!confirm_end) {
		return false;
	}
	var continue_search_checked = continue_search.length>0 && continue_search[0].checked;
	if (continue_search_checked) {
		ended = true;
		localStorage.setItem("autoprompt", "yes");
	}
	if (ws.readyState==1) {
		$.post(this.action, {}, function() {
			if (continue_search_checked) {
				location.href="/";
			}
		});
		return false;
	}
});
var continue_search = $("#continue_search");

function ping() {
	if (ws.readyState==1) {
		ws.send('{"action":"ping"}');
		window.setTimeout(ping, 8000);
	}
}

function render_message(message) {
	// Check if we're at the bottom before rendering because rendering will mean that we're not.
	var scroll_after_render = is_at_bottom();
	if (message.symbol) {
		if (message.type=="system") {
			var text = message.text.replace("%s", message.symbol);
		} else {
			var text = message.symbol+": "+message.text;
		}
	} else {
		var text = message.text;
	}
	var li = $("<li>").addClass("tile message_"+message.type);
	var p = $("<p>").css("color", "#"+message.colour).text(text).appendTo(li);
	li.appendTo(messages);
	if (scroll_after_render) {
		scroll_to_bottom();
	}
	if (document.hidden || document.webkitHidden || document.msHidden) {
		document.title = "New message - CHERUBPLAY";
	}
}

if (typeof WebSocket!="undefined") {
	var ws_protocol = (location.protocol=="https:") ? "wss://" : "ws://";
	var ws = new WebSocket(ws_protocol+location.host+"/live/"+chat_url+"/");
	ws.onopen = function(e) {
		window.setTimeout(ping, 8000);
		scroll_to_bottom();
		if (document.hidden || document.webkitHidden || document.msHidden) {
			document.title = "Connected - CHERUBPLAY";
		}
	}
	ws.onmessage = function(e) {
		if (!ended) {
			message = JSON.parse(e.data);
			if (message.action=="message") {
				render_message(message.message);
				var d = new Date();
				last_status_message = "Last message: "+d.toLocaleDateString()+" "+d.toLocaleTimeString()
				status_bar.text(last_status_message);
			} else if (message.action=="end") {
				ws.close();
				if (continue_search.length>0 && continue_search[0].checked) {
					continue_timeout = window.setTimeout(function() {
						localStorage.setItem("autoprompt", "yes");
						window.location = "/";
					}, 3000);
					status_bar.text("Searching again in a few seconds. Click to cancel.").click(function() {
						window.clearTimeout(continue_timeout);
						status_bar.remove();
					});
				} else {
					status_bar.remove();
				}
				message_form_container.remove();
				render_message(message.message);
			} else if (message.action=="typing") {
				status_bar.text(message.symbol+" is typing.");
			} else if (message.action=="stopped_typing") {
				status_bar.text(last_status_message);
			} else if (message.action=="online") {
				last_status_message = message.symbol+" is online.";
				status_bar.text(last_status_message);
			} else if (message.action=="offline") {
				last_status_message = message.symbol+" is now offline. They will be notified of any messages you send when they next visit.";
				status_bar.text(last_status_message);
			}
		}
	}
	ws.onclose = function(e) {
		if (!e.wasClean) {
			status_bar.text("Live updates currently unavailable. Please refresh to see new messages.");
		}
	}
	if (typeof document.hidden !== "undefined") {
		document.addEventListener("visibilitychange", visibility_handler);
	} else if (typeof document.msHidden !== "undefined") {
		document.addEventListener("msvisibilitychange", visibility_handler);
	} else if (typeof document.webkitHidden !== "undefined") {
		document.addEventListener("webkitvisibilitychange", visibility_handler);
	}
} else {
	var ws = {
		readyState: 3,
	};
	status_bar.text("Live updates are not available because your browser does not appear to support WebSockets. Please refresh to see new messages.");
}
