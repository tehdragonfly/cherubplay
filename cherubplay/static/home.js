var prompt_list = document.getElementById("prompt_list");

function render_prompt(prompt) {
	var li = $("<li>").attr("id", prompt.id).addClass("tile");
	$("<p>").css("color", prompt.colour).text(prompt.prompt).appendTo(li);
	//$("<button>").text("Answer").appendTo(li);
	li.appendTo(prompt_list);
}

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
	ws.send('{"action":"search"}');
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
	}
}

ws.onclose = function(e) {
	alert("closed");
}
