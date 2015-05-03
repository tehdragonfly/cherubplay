var cherubplay = (function() {

	var colour_regex = /^#[0-9a-f]{6}$/i;

	var body = $(document.body);
	var header = $("header");
	var header_height = header.height();
	var nav = $("#nav");

	// Fallback for sticky navigation.
	if (nav.css("position") == "static") {
		console.log("No position:sticky.");
		$(window).scroll(function() {
			var nav_position = nav.css("position");
			if (nav_position == "static" && window.scrollY > header_height) {
				header.css("padding-bottom", nav.height());
				nav.css("position", "fixed");
			} else if (nav_position == "fixed" && window.scrollY < header_height) {
				header.css("padding-bottom", 0);
				nav.css("position", "static");
			}
		});
		$(window).resize(function() {
			header_height = header.height();
		});
	}

	return {
		"home": function() {

			// Modes

			function change_mode(new_mode) {
				body.removeClass("answer_mode").removeClass("prompt_mode").removeClass("wait_mode");
				if (ws.readyState==1 && new_mode=="answer_mode") {
					ws.send(JSON.stringify({
						"action": "search",
						"categories": answer_string(answer_categories),
						"levels": answer_string(answer_levels),
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

			function change_answer_mode() {
				change_mode("answer_mode");
			}

			function load_checkboxes(index, checkbox) {
				var checked = localStorage.getItem("answer_"+checkbox.name);
				// Check Homestuck and SFW by default.
				// Should we do this as a dict?
				if (!checked && (checkbox.name == "homestuck" || checkbox.name == "sfw")) {
					checkbox.checked = true;
				} else {
					checkbox.checked = checked == "true";
				}
			}

			var answer_categories = $("#answer_categories input").change(change_answer_mode).each(load_checkboxes);
			var answer_levels = $("#answer_levels input").change(change_answer_mode).each(load_checkboxes);

			function answer_string(checkboxes) {
				var array = []
				checkboxes.each(function(index, checkbox) {
					localStorage.setItem("answer_"+checkbox.name, checkbox.checked);
					if (checkbox.checked) {
						array.push(checkbox.name);
					}
				});
				return array.toString();
			}

			var filter_toggle = $("#filter_toggle");

			var filter_sites = $("#filter_sites input").each(function(index, checkbox) {
				checkbox.checked = localStorage.getItem("filter_"+checkbox.name) == "true";
			});

			var filter_custom = $("#filter_custom");
			var saved_filter_custom = localStorage.getItem("filter_custom");
			if (saved_filter_custom) {
				filter_custom.text(saved_filter_custom);
			}

			function make_filter_phrases() {
				// Allow delimiting by comma or linebreak.
				// Trim and lowercase.
				// Filter empty phrases.
				var filter_phrases = $("#filter_custom").val().replace("\n", ",", "g").split(",").map(
					function(phrase) { return phrase.trim().toLowerCase(); }
				).filter(
					function(phrase) { return phrase; }
				);
				filter_sites.each(function(index, checkbox) {
					if (checkbox.checked) {
						filter_phrases.push(checkbox.name);
					}
				});
				return filter_phrases;
			}
			var filter_phrases = make_filter_phrases();

			var filter_form = $("#categories form").submit(function() {
				filter_sites.each(function(index, checkbox) {
					localStorage.setItem("filter_"+checkbox.name, checkbox.checked);
				});
				localStorage.setItem("filter_custom", filter_custom.val());
				filter_phrases = make_filter_phrases();
				filter_toggle[0].checked = false;
				change_mode("answer_mode");
				return false;
			});

			var prompt_list = $("#prompt_list");

			function check_filter_phrases(prompt) {
				var prompt_text = prompt.prompt.toLowerCase();
				for (var i=0; i<filter_phrases.length; i++) {
					if (prompt_text.indexOf(filter_phrases[i]) != -1) {
						return false;
					}
				}
				return true;
			}

			function render_prompt(prompt) {
				if (filter_phrases.length == 0 || check_filter_phrases(prompt)) {
					var li = $("<li>").attr("id", prompt.id).addClass("tile").click(show_overlay);
					$("<p>").css("color", "#"+prompt.colour).text(prompt.prompt).appendTo(li);
					$("<div>").addClass("fade").appendTo(li);
					li.appendTo(prompt_list);
				}
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
			$("#overlay .tile").click(function(e) { e.stopPropagation(); });
			$("#overlay_answer").click(function(e) {
				if (overlay_prompt_id) {
					ws.send(JSON.stringify({
						"action": "answer",
						"id": overlay_prompt_id,
					}));
					hide_overlay();
				}
			});
			$("#overlay_report").click(function(e) {
				if (overlay_prompt_id) {
					$("#report_overlay input").prop("checked", false);
					report_category.val("homestuck");
					report_level.val("sfw");
					body.addClass("show_report_overlay");
				}
			});

			function hide_report_overlay() {
				body.removeClass("show_report_overlay");
			}

			$("#report_overlay").click(hide_report_overlay);
			$("#report_overlay_close").click(hide_report_overlay);
			$("#report_overlay .tile").click(function(e) { e.stopPropagation(); });
			$("#report_overlay_submit").click(function() {
				var reason = $("#report_overlay input:checked").val();
				if (!reason) {
					alert("Please select a reason.");
					return;
				}
				ws.send(JSON.stringify({
					"action": "report",
					"id": overlay_prompt_id,
					"reason": reason,
					"category": report_category.val(),
					"level": report_level.val(),
				}));
				hide_report_overlay();
				hide_overlay();
				alert("Thanks for the report!");
			});
			var report_category = $("#report_category");
			var report_level = $("#report_level");

			// Prompt mode

			var prompt_form = $("#prompt_mode form").submit(function(e) {
				if (!colour_regex.test(prompt_colour.val())) {
					alert("The colour needs to be a valid hex code, for example \"#0715CD\" or \"#416600\".");
					return false;
				}
				if (prompt_category.val() == "" || prompt_level.val() == "") {
					alert("Please choose a category and level for your prompt.")
					return false;
				}
				prompt_text.val(prompt_text.val().trim());
				if (prompt_text.val()=="") {
					alert("You can't submit a blank prompt.")
					return false;
				}
				localStorage.setItem("prompt_colour", prompt_colour.val());
				localStorage.setItem("prompt_text", prompt_text.val());
				localStorage.setItem("prompt_category", prompt_category.val());
				localStorage.setItem("prompt_level", prompt_level.val());
				change_mode("wait_mode");
				ws.send(JSON.stringify({
					"action": "prompt",
					"colour": prompt_colour.val().substr(1, 6),
					"prompt": prompt_text.val(),
					"category": prompt_category.val(),
					"level": prompt_level.val(),
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
				prompt_category.val("");
				prompt_level.val("");
				this.style.height = this.scrollHeight+"px";
			});
			var prompt_category = $("#prompt_category");
			var prompt_level = $("#prompt_level");

			var saved_prompt_colour = localStorage.getItem("prompt_colour");
			var saved_prompt_text = localStorage.getItem("prompt_text");
			var saved_prompt_category = localStorage.getItem("prompt_category");
			var saved_prompt_level = localStorage.getItem("prompt_level");
			if (saved_prompt_colour && saved_prompt_text) {
				prompt_colour.val(saved_prompt_colour).change();
				prompt_text.text(saved_prompt_text);
			}
			if (saved_prompt_category) {
				prompt_category.val(saved_prompt_category);
			}
			if (saved_prompt_level) {
				prompt_level.val(saved_prompt_level);
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
				var last_mode = localStorage.getItem("last_mode");
				var autoprompt = localStorage.getItem("autoprompt");
				if (last_mode=="prompt_mode" && autoprompt && saved_prompt_colour && saved_prompt_text && saved_prompt_category && saved_prompt_level) {
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
					$(prompt_list).empty();
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
		"account": function() {
			var sound_notifications = $("#sound_notifications").click(function() {
				localStorage.setItem("sound_notifications", this.checked);
				if (this.checked) {
					$("#confirmation").text("Sound notifications are now enabled.");
				} else {
					$("#confirmation").text("Sound notifications are now disabled.");
				}
				window.scroll(0, 0);
			});
			if (localStorage.getItem("sound_notifications") == "true") {
				sound_notifications.attr("checked", "checked");
			}
		},
		"chat": function(chat_url, own_symbol) {

			// Hook so we can get colours in hex format.
			$.cssHooks.color = {
				get: function(elem) {
					if (elem.currentStyle) {
						var col = elem.currentStyle["color"];
					} else if (window.getComputedStyle) {
						var col = document.defaultView.getComputedStyle(elem, null).getPropertyValue("color");
					}
					if (col.search("rgb") == -1) {
						return col;
					} else {
						col = col.match(/^rgb\((\d+),\s*(\d+),\s*(\d+)\)$/);
						function hex(x) {
							return ("0" + parseInt(x).toString(16)).slice(-2);
						}
						return "#" + hex(col[1]) + hex(col[2]) + hex(col[3]);
					}
				}
			}

			var original_title = document.title;

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
					document.title = original_title;
				}, 200);
			}

			var messages = $("#messages");

			var editing_id, pre_edit_color, pre_edit_ooc, pre_edit_text;

			function start_editing() {
				if (ended) {
					return;
				}
				var jquery_this = $(this);
				var editing_this = jquery_this.hasClass("editing");
				if (editing_this) {
					cancel_editing();
				} else {
					$(".editing").removeClass("editing");
					if (!editing_id) {
						pre_edit_color = message_colour.val();
						pre_edit_ooc = message_ooc[0].checked;
						pre_edit_text = message_text.val();
					}
					editing_id = jquery_this.attr("id").substr(8);
					message_form.attr("action", "/chats/"+chat_url+"/edit/"+editing_id+"/");
					jquery_this.addClass("editing");
					message_form_container.addClass("editing");
					var paragraph = jquery_this.find("p");
					message_colour.val(paragraph.css("color")).change();
					message_ooc[0].checked = jquery_this.hasClass("message_ooc");
					message_text.css("height", "100px").val(paragraph.text().substr(3)).keyup();
					message_form.find("button").text("Edit");
					window.scrollTo(0, message_form_container.position()["top"]-50);
					message_text.focus();
				}
			}

			function cancel_editing() {
				$(".editing").removeClass("editing");
				editing_id = null;
				message_form.attr("action", "/chats/"+chat_url+"/send/");
				message_colour.val(pre_edit_color).change();
				message_ooc[0].checked = pre_edit_ooc;
				message_text.css("height", "100px").val(pre_edit_text).change().keyup();
				message_form.find("button").text("Send");
				window.scrollTo(0, message_form_container.position()["top"]-50);
			}

			$("#messages li[data-symbol="+own_symbol+"]").dblclick(start_editing);

			var status_bar = $("#status_bar");
			var last_status_message = status_bar.text();

			var message_form_container = $("#message_form_container").dblclick(function() {
				if ($(this).hasClass("editing")) {
					cancel_editing();
				}
			});
			var message_form = $("#message_form").submit(function() {
				if (!colour_regex.test(message_colour.val())) {
					alert("The colour needs to be a valid hex code, for example \"#0715CD\" or \"#416600\".");
					return false;
				}
				message_text.val(message_text.val().trim());
				if (message_text.val()=="") {
					alert("You can't submit a blank message.")
					return false;
				}
				typing = false;
				window.clearTimeout(typing_timeout);
				if (ws.readyState==1) {
					$.ajax({
						"url": this.action,
						"method": "POST",
						"data": message_form.serializeArray(),
						"success": function() {
							message_text.val("").css("height", "100px");
							if (message_form_container.hasClass("editing")) {
								cancel_editing();
							}
						},
						"error": function() {
							if (message_form_container.hasClass("editing")) {
								alert("There was a problem editing your message.");
							} else {
								alert("There was an error with your message. Please try again later.");
							}
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
			var message_ooc = $("#message_ooc");
			var message_text = $("#message_text").keypress(function(e) {
				if (ws.readyState==1) {
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

			var search_again = $("#search_again").click(function() {
				localStorage.setItem("autoprompt", "yes");
			});

			var notification_audio;
			if (localStorage.getItem("sound_notifications") == "true") {
				var notification_audio = $("<audio>");
				$("<source>").attr("src", "/static/carne_vale.ogg").appendTo(notification_audio);
				$("<source>").attr("src", "/static/carne_vale.mp3").appendTo(notification_audio);
			}

			function ping() {
				if (ws.readyState==1) {
					ws.send('{"action":"ping"}');
					window.setTimeout(ping, 8000);
				}
			}

			function render_message(message) {
				// Check if we're at the bottom before rendering because rendering will mean that we're not.
				var scroll_after_render = is_at_bottom();
				var li = $("<li>").attr("id", "message_"+message.id).addClass("tile message_"+message.type);
				if (message.symbol) {
					li.attr("data-symbol", message.symbol);
					if (message.symbol == own_symbol) {
						li.dblclick(start_editing);
					}
					if (message.type == "system") {
						var text = message.text.replace("%s", message.symbol);
					} else {
						var text = message.symbol+": "+message.text;
					}
				} else {
					var text = message.text;
				}
				var p = $("<p>").css("color", "#"+message.colour).text(text).appendTo(li);
				li.appendTo(messages);
				if (scroll_after_render) {
					scroll_to_bottom();
				}
				if (document.hidden || document.webkitHidden || document.msHidden) {
					document.title = "New message - " + original_title;
					if (notification_audio) {
						notification_audio[0].play();
					}
				}
			}

			if (typeof WebSocket!="undefined") {
				var ws;
				var ws_works = false;
				var ws_connected_time = 0;
				function launch_websocket() {
					var ws_protocol = (location.protocol=="https:") ? "wss://" : "ws://";
					ws = new WebSocket(ws_protocol+location.host+"/live/"+chat_url+"/");
					ws.onopen = ws_onopen;
					ws.onmessage = ws_onmessage;
					ws.onclose = ws_onclose;
				}
				function ws_onopen(e) {
					ws_works = true;
					ws_connected_time = Date.now();
					window.setTimeout(ping, 8000);
					status_bar.text(last_status_message);
					scroll_to_bottom();
					if (document.hidden || document.webkitHidden || document.msHidden) {
						document.title = "Connected - " + original_title;
						if (notification_audio) {
							notification_audio[0].play();
						}
					}
				}
				function ws_onmessage(e) {
					if (!ended) {
						message = JSON.parse(e.data);
						if (message.action=="message") {
							render_message(message.message);
							var d = new Date();
							last_status_message = "Last message: "+d.toLocaleDateString()+" "+d.toLocaleTimeString();
							status_bar.text(last_status_message);
						} else if (message.action=="edit") {
							status_bar.text(last_status_message);
							var li = $("#message_"+message.message.id);
							if (li.length == 0) {
								return;
							}
							li.removeClass("message_ic").removeClass("message_ooc").addClass("message_"+message.message.type);
							if (message.message.show_edited) {
								li.addClass("edited");
							}
							var p = li.find("p").css("color", "#"+message.message.colour).text(message.message.symbol+": "+message.message.text);
						} else if (message.action=="end") {
							ws.close();
							ended = true;
							$(".editing").removeClass("editing");
							if (search_again.length>0) {
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
				function ws_onclose(e) {
					status_bar.text("Live updates currently unavailable. Please refresh to see new messages.");
					// Only try to re-connect if we've managed to connect before.
					console.log(Date.now() - ws_connected_time);
					if (ws_works && (Date.now() - ws_connected_time) >= 5000) {
						window.setTimeout(launch_websocket, 2000);
					}
				}
				if (typeof document.hidden !== "undefined") {
					document.addEventListener("visibilitychange", visibility_handler);
				} else if (typeof document.msHidden !== "undefined") {
					document.addEventListener("msvisibilitychange", visibility_handler);
				} else if (typeof document.webkitHidden !== "undefined") {
					document.addEventListener("webkitvisibilitychange", visibility_handler);
				}
				launch_websocket();
			} else {
				var ws = {
					readyState: 3,
				};
				status_bar.text("Live updates are not available because your browser does not appear to support WebSockets. Please refresh to see new messages.");
			}

		},
	}
})();

