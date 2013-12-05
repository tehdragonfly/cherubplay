// Modes

function change_mode(new_mode) {
	var body = $(document.body);
	body.removeClass("answer_mode").removeClass("prompt_mode").removeClass("wait_mode");
	if (ws.readyState==1 && new_mode=="answer_mode") {
		ws.send('{"action":"search"}');
		body.addClass("answer_mode");
		localStorage.setItem("last_mode", "answer_mode");
	} else if (ws.readyState==1 && new_mode=="prompt_mode") {
		ws.send('{"action":"idle"}');
		body.addClass("prompt_mode");
		localStorage.setItem("last_mode", "prompt_mode");
	} else if (ws.readyState==1 && new_mode=="wait_mode") {
		body.addClass("wait_mode");
	} else if (ws.readyState==3) {
		body.addClass("connection_error");
	}
}

$(".prompt_button").click(function() { change_mode("prompt_mode") });
$(".answer_button").click(function() { change_mode("answer_mode") });

// Answer mode

var prompt_list = document.getElementById("prompt_list");

function render_prompt(prompt) {
	var li = $("<li>").attr("id", prompt.id).addClass("tile");
	$("<p>").css("color", "#"+prompt.colour).text(prompt.prompt).appendTo(li);
	$("<button>").text("Answer").appendTo(li).click(function(e) {
		ws.send(JSON.stringify({
			"action": "answer",
			"id": this.parentNode.id,
		}));
	});
	li.appendTo(prompt_list);
}

// Prompt mode

var colour_regex = /^#[0-9a-f]{6}$/i;
var prompt_form = $("#prompt_mode form").submit(function(e) {
	if (!colour_regex.test(prompt_colour.val())) {
		alert("The colour needs to be a valid hex code, for example \"#0715CD\" or \"#416600\".");
		return false;
	}
	prompt_text.val(prompt_text.val().trim());
	if (prompt_text.val()=="") {
		alert("You can't submit a blank prompt.")
		return false;
	}
	localStorage.setItem("prompt_colour", prompt_colour.val());
	localStorage.setItem("prompt_text", prompt_text.val());
	change_mode("wait_mode");
	ws.send(JSON.stringify({
		"action": "prompt",
		"colour": prompt_colour.val().substr(1, 6),
		"prompt": prompt_text.val(),
	}));
	return false;
});
var prompt_colour = $("#prompt_colour").change(function() {
	prompt_text.css("color", this.value);
});
var preset_colours = $("#preset_colours").change(function() {
	prompt_colour.val(this.value).change();
});
var prompt_text = $("#prompt_text").keyup(function() {
	this.style.height = this.scrollHeight+"px";
});

var saved_prompt_colour = localStorage.getItem("prompt_colour");
var saved_prompt_text = localStorage.getItem("prompt_text");
if (saved_prompt_colour && saved_prompt_text) {
	prompt_colour.val(saved_prompt_colour).change();
	prompt_text.text(saved_prompt_text);
}

// Communication

function ping() {
	if (ws.readyState==1) {
		ws.send('{"action":"ping"}');
		window.setTimeout(ping, 8000);
		console.log("ping");
	}
}

var ws = new WebSocket("ws://www.cherubplay.tk/search/");

ws.onopen = function(e) {
	window.setTimeout(ping, 8000);
	last_mode = localStorage.getItem("last_mode");
	if (last_mode) {
		change_mode(last_mode);
	} else {
		change_mode("answer_mode");
	}
}

ws.onmessage = function(e) {
	message = JSON.parse(e.data);
	if (message.action=="prompts") {
		$(prompt_list).empty()
		for (var i=0; i<message.prompts.length; i++) {
			render_prompt(message.prompts[i]);
		}
	} else if (message.action=="new_prompt") {
		render_prompt(message);
	} else if (message.action=="remove_prompt") {
		$("#"+message.id).remove();
	} else if (message.action=="answer_error") {
		alert(message.error);
		change_mode("answer_mode");
	} else if (message.action=="prompt_error") {
		change_mode("prompt_mode");
		alert(message.error);
	} else if (message.action=="chat") {
		change_mode();
		window.location.href="/chats/"+message.url+"/";
	}
}

ws.onclose = function(e) {
	if (!e.wasClean) {
		change_mode();
	}
}
