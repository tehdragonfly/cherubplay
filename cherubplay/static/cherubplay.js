var cherubplay = (function() {
	var body = $(document.body);
	var colour_regex = /^#(E0(07){2}|(41[6]{2}|[F][C]{0}2A[4]{1})00)$/i;
	return {
		"chat_list": function() {

			$(".delete_form").submit(function() {
				var confirm_end = confirm("Are you sure you want to delete this chat? This cannot be undone.");
				if (confirm_end) {
					$.post(this.action);
					this.parentNode.remove();
				}
				return false;
			});

		},
		"home": function() {

			// Modes

			function change_mode(new_mode) {
				body.removeClass("answer_mode").removeClass("prompt_mode").removeClass("wait_mode");
				if (ws.readyState==1 && new_mode=="answer_mode") {
					ws.send(JSON.stringify({
						"action": "search",
						"nsfw": (show_nsfw[0].checked==true),
					}));
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

			var show_nsfw = $("#show_nsfw").click(function() {
				localStorage.setItem("show_nsfw", this.checked);
				change_mode("answer_mode");
			});

			var prompt_list = $("#prompt_list");

			function render_prompt(prompt) {
				var li = $("<li>").attr("id", prompt.id).addClass("tile").click(show_overlay);
				$("<p>").css("color", "#"+prompt.colour).text(prompt.prompt).appendTo(li);
				$("<div>").addClass("fade").appendTo(li);
				li.appendTo(prompt_list);
			}

			var overlay_prompt_id;
			var overlay_text = $("#overlay_text");

			function show_overlay() {
				var prompt = $(this).find("p");
				overlay_prompt_id = this.id;
				overlay_text.css("color", prompt.css("color")).text(prompt.text());
				body.addClass("show_overlay");
			}

			function hide_overlay() {
				body.removeClass("show_overlay");
				overlay_prompt_id = null;
			}

			$("#overlay").click(hide_overlay);
			$("#overlay_close").click(hide_overlay);
			$("#overlay_tile").click(function(e) { e.stopPropagation(); });
			$("#overlay_answer").click(function(e) {
				if (overlay_prompt_id) {
					ws.send(JSON.stringify({
						"action": "answer",
						"id": overlay_prompt_id,
					}));
					hide_overlay();
				}
			});

			// Prompt mode

			var prompt_form = $("#prompt_mode form").submit(function(e) {
				if (!colour_regex.test(prompt_colour.val())) {
					alert("strider colors only");
					alert("that means #E00707 or #F2A400");
					return false;
				}
				prompt_text.val(prompt_text.val().trim());
				if (prompt_text.val()=="") {
					alert("come on man shaq didnt die for this");
					return false;
				}
				localStorage.setItem("prompt_colour", prompt_colour.val());
				localStorage.setItem("prompt_text", prompt_text.val());
				localStorage.setItem("prompt_nsfw", prompt_nsfw[0].checked);
				change_mode("wait_mode");
				ws.send(JSON.stringify({
					"action": "prompt",
					"colour": prompt_colour.val().substr(1, 6),
					"prompt": prompt_text.val(),
					"nsfw": prompt_nsfw[0].checked,
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
			var prompt_nsfw = $("#prompt_nsfw");

			var saved_prompt_colour = localStorage.getItem("prompt_colour");
			var saved_prompt_text = localStorage.getItem("prompt_text");
			var saved_prompt_nsfw = localStorage.getItem("prompt_nsfw");
			if (saved_prompt_colour && saved_prompt_text) {
				if (["#e00707", "#f2a400"].indexOf(saved_prompt_colour.toLowerCase())==-1) {
					prompt_colour.val("#e00707").change();
				} else {
					prompt_colour.val(saved_prompt_colour).change();
				}
				prompt_text.text(saved_prompt_text);
				prompt_nsfw[0].checked = (localStorage.getItem("prompt_nsfw")=="true");
			}

			// Communication

			function ping() {
				if (ws.readyState==1) {
					ws.send('{"action":"ping"}');
					window.setTimeout(ping, 8000);
					console.log("ping");
				}
			}

			var ws_protocol = (location.protocol=="https:") ? "wss://" : "ws://";
			var ws = new WebSocket(ws_protocol+location.host+"/search/");

			ws.onopen = function(e) {
				window.setTimeout(ping, 8000);
				show_nsfw[0].checked = (localStorage.getItem("show_nsfw")=="true");
				var last_mode = localStorage.getItem("last_mode");
				var autoprompt = localStorage.getItem("autoprompt");
				if (last_mode=="prompt_mode" && autoprompt && saved_prompt_colour && saved_prompt_text) {
					prompt_form.submit();
				} else if (last_mode) {
					change_mode(last_mode);
				} else {
					change_mode("answer_mode");
				}
				localStorage.removeItem("autoprompt");
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
					if (message.id==overlay_prompt_id) {
						hide_overlay();
						alert("Sorry, either this prompt has been taken or the prompter has disconnected :(");
					}
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

		},
		"chat": function(chat_url) {

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
					document.title = "striderplay";
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
					alert("strider colors only");
					alert("that means #E00707 or #F2A400");
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
					document.title = "new message - striderplay";
				}
			}

			if (typeof WebSocket!="undefined") {
				var ws_protocol = (location.protocol=="https:") ? "wss://" : "ws://";
				var ws = new WebSocket(ws_protocol+location.host+"/live/"+chat_url+"/");
				ws.onopen = function(e) {
					window.setTimeout(ping, 8000);
					scroll_to_bottom();
					if (document.hidden || document.webkitHidden || document.msHidden) {
						document.title = "connected - striderplay";
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

		},
	}
})();

