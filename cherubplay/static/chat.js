
var colour_regex = /^#[0-9a-f]{6}$/i;

var messages = $("#messages");
var status_bar = $("#status_bar");
var message_form = $("#message_form");
var message_colour = $("#message_colour").change(function() {
	message_text.css("color", this.value);
});
var message_text = $("#message_text").keypress(function(e) {
	if (e.keyCode==13 && !e.shiftKey) {
		message_form.submit();
		return false;
	}
});

function ping() {
	if (ws.readyState==1) {
		ws.send('{"action":"ping"}');
		window.setTimeout(ping, 8000);
		console.log("ping");
	}
}

function render_message(message) {
	if (message.symbol) {
		var text = message.symbol+": "+message.text;
	} else {
		var text = message.text;
	}
	var li = $("<li>").addClass("tile message_"+message.type);
	var p = $("<p>").css("color", "#"+message.colour).text(text).appendTo(li);
	li.appendTo(messages);
	window.scroll(0, document.documentElement.scrollHeight-document.documentElement.clientHeight);
}

var ws = new WebSocket("ws://www.cherubplay.tk/live/"+chat_url+"/");

ws.onopen = function(e) {
	window.setTimeout(ping, 8000);
	message_form.submit(function() {
		if (!colour_regex.test(message_colour.val())) {
			alert("The colour needs to be a valid hex code, for example \"#0715CD\" or \"#416600\".");
			return false;
		}
		message_text.val(message_text.val().trim());
		if (message_text.val()=="") {
			alert("You can't submit a blank message.")
			return false;
		}
		$.ajax({
			"url": this.action,
			"method": "POST",
			"data": message_form.serializeArray(),
			"success": function() {
				message_text.val("")
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
	});
	window.scroll(0, document.documentElement.scrollHeight-document.documentElement.clientHeight);
}

ws.onmessage = function(e) {
	message = JSON.parse(e.data);
	if (message.action=="message") {
		render_message(message.message);
	}
}

ws.onclose = function(e) {
	if (!e.wasClean) {
		status_bar.text("Live updates currently unavailable. Please refresh to see new messages.");
	}
}

