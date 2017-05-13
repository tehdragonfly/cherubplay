var cherubplay = (function() {

	function urlBase64ToUint8Array(base64String) {
		const padding = '='.repeat((4 - base64String.length % 4) % 4);
		const base64 = (base64String + padding).replace(/\-/g, '+').replace(/_/g, '/');
		const rawData = window.atob(base64);
		return Uint8Array.from([...rawData].map((char) => char.charCodeAt(0)));
	}

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

	$(".expandable .toggle").click(function() {
		var expandable_toggle = $(this);
		var expanded_content = expandable_toggle.next(".expanded_content");
		if (expanded_content.html()) {
			expandable_toggle.parent().toggleClass("expanded");
		} else {
			$.get(expanded_content.attr("data-href"), function(data) {
				switch (expanded_content.attr("data-type")) {
					case "prompt":
						var text = data.text;
						break;
					case "prompt_report":
						var text = data.prompt;
						break;
					case "request_ooc_notes":
						var text = data.request.ooc_notes;
						break;
					case "request_starter":
						var text = data.request.starter;
						break;
					case "chat":
						var text = data.messages[0].text;
						break;
				}
				expanded_content.text(text);
				expandable_toggle.parent().addClass("expanded");
			});
		}
		return false;
	});

	function is_at_bottom() {
		return window.scrollY == document.documentElement.scrollHeight - document.documentElement.clientHeight;
	}

	function scroll_to_bottom() {
		window.scroll(0, document.documentElement.scrollHeight - document.documentElement.clientHeight);
	}

	$("textarea").keyup(function() {
		// Check if we're at the bottom before resizing because resizing will mean that we're not.
		var scroll_after_resize = is_at_bottom();
		this.style.height = this.scrollHeight + "px";
		if (scroll_after_resize) {
			scroll_to_bottom();
		}
	});

	return {
		"home": function() {

			// Modes

			function change_mode(new_mode) {
				body.removeClass("answer_mode").removeClass("prompt_mode").removeClass("wait_mode");
				if (ws.readyState==1 && new_mode=="answer_mode") {
					ws.send(JSON.stringify({
						"action": "search",
						"categories": answer_string(answer_categories),
						"starters": answer_string(answer_starters),
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
				if (!checked && (["homestuck", "starter", "no-starter", "sfw"].indexOf(checkbox.name) != -1)) {
					checkbox.checked = true;
				} else {
					checkbox.checked = checked == "true";
				}
			}

			var answer_categories = $("#answer_categories input").change(change_answer_mode).each(load_checkboxes);
			var answer_starters = $("#answer_starters input").change(change_answer_mode).each(load_checkboxes);
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

			var tile_class = body.hasClass("layout2") ? "tile2" : "tile";

			var prompt_data = {};

			function render_prompt(prompt) {
				if (filter_phrases.length == 0 || check_filter_phrases(prompt)) {
					prompt_data[prompt.id] = prompt;
					var li = $("<li>").attr("id", prompt.id).addClass(tile_class).click(show_overlay);
					$("<p>").css("color", "#"+prompt.colour).text(prompt.prompt).appendTo(li);
					$("<div>").addClass("fade").appendTo(li);
					li.appendTo(prompt_list);
				}
			}

			var overlay_prompt_id;
			var overlay = $("#overlay");
			var overlay_report_and_close = $("#overlay_report_and_close");
			var overlay_text = $("#overlay_text");
			var overlay_images = $("#overlay_images").click(function(e) { e.stopPropagation(); });

			function show_overlay() {
				var prompt = $(this).find("p");
				overlay_prompt_id = this.id;
				overlay_text.css("color", prompt.css("color")).text(prompt.text());
				if (body.hasClass("layout2") && prompt_data[this.id] && prompt_data[this.id].images) {
					var images = prompt_data[this.id].images
					for (var i = 0; i < images.length; i++) {
						$("<img>").addClass("tile2").attr("src", images[i]).appendTo(overlay_images);
					}
				}
				body.addClass("show_overlay");

				if (
					overlay_report_and_close.length == 1
					// Sticky positioning doesn't work or we've run this before.
					&& ["sticky", "-webkit-sticky", "fixed"].indexOf(getComputedStyle(overlay_report_and_close[0]).position) == -1
				) {
					overlay_report_and_close.addClass("fallback").css("height", overlay_report_and_close.find(".tile2").outerHeight() + "px");
				}

				overlay.scrollTop(0);
			}

			function hide_overlay() {
				body.removeClass("show_overlay");
				overlay_prompt_id = null;
				overlay_images.empty();
			}

			$("#overlay").click(hide_overlay);
			$("#overlay_close").click(hide_overlay);
			$("#overlay ." + tile_class).click(function(e) { e.stopPropagation(); });
			$("#overlay_answer").click(function(e) {
				if (overlay_prompt_id) {
					ws.send(JSON.stringify({
						"action": "answer",
						"id": overlay_prompt_id,
					}));
					hide_overlay();
				}
				e.stopPropagation();
			});
			$("#overlay_report").click(function(e) {
				if (overlay_prompt_id) {
					$("#report_overlay input").prop("checked", false);
					report_category.val("homestuck");
					report_starter.val("starter");
					report_level.val("sfw");
					body.addClass("show_report_overlay");
				}
			});

			function hide_report_overlay() {
				body.removeClass("show_report_overlay");
			}

			$("#report_overlay").click(hide_report_overlay);
			$("#report_overlay_close").click(hide_report_overlay);
			$("#report_overlay ." + tile_class).click(function(e) { e.stopPropagation(); });
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
					"starter": report_starter.val(),
					"level": report_level.val(),
				}));
				hide_report_overlay();
				hide_overlay();
				alert("Thanks for the report!");
			});
			var report_category = $("#report_category");
			var report_starter = $("#report_starter");
			var report_level = $("#report_level");

			// Prompt mode

			var prompt_form = $("#prompt_mode form").submit(function(e) {
				if (prompt_id.length > 0 && prompt_info.css("display") == "none") {
					change_mode("wait_mode");
					$.ajax("/prompts/" + prompt_id.val() + ".json", {
						success: function(data) {
							if (!data.category) {
								alert("This prompt doesn't have a category. Please double-check the categories on your prompts page.");
								change_mode("prompt_mode");
								return;
							}
							localStorage.setItem("new_or_saved_prompt", "saved_prompt");
							localStorage.setItem("prompt_id", prompt_id.val());
							ws.send(JSON.stringify({
								"action": "prompt",
								"colour": data.colour,
								"prompt": data.text,
								"category": data.category,
								"starter": data.starter,
								"level": data.level,
							}));
						},
						error: function() {
							alert("Sorry, that prompt couldn't be found.");
							change_mode("prompt_mode");
						},
					});
					return false;
				}
				localStorage.setItem("new_or_saved_prompt", "new_prompt");
				if (!colour_regex.test(prompt_colour.val())) {
					alert("The colour needs to be a valid hex code, for example \"#0715CD\" or \"#416600\".");
					return false;
				}
				if (prompt_category.val() == "" || prompt_starter.val() == "" || prompt_level.val() == "") {
					alert("Please choose a category, starter and level for your prompt.")
					return false;
				}
				prompt_text.val(prompt_text.val().trim());
				if (prompt_text.val()=="") {
					alert("You can't submit a blank prompt.");
					return false;
				}
				localStorage.setItem("prompt_colour", prompt_colour.val());
				localStorage.setItem("prompt_text", prompt_text.val());
				localStorage.setItem("prompt_category", prompt_category.val());
				localStorage.setItem("prompt_starter", prompt_starter.val());
				localStorage.setItem("prompt_level", prompt_level.val());
				change_mode("wait_mode");
				ws.send(JSON.stringify({
					"action": "prompt",
					"colour": prompt_colour.val().substr(1, 6),
					"prompt": prompt_text.val(),
					"category": prompt_category.val(),
					"starter": prompt_starter.val(),
					"level": prompt_level.val(),
				}));
				return false;
			});
			var prompt_info = $("#prompt_info");
			$("#saved_prompt, #new_prompt").change(function() {
				if (this.checked) {
					prompt_info.css("display", this.value == "new" ? "block" : "none");
				}
			}).change();
			var prompt_id = $("#prompt_id");
			var prompt_colour = $("#prompt_colour").change(function() {
				prompt_text.css("color", this.value);
			});
			var preset_colours = $("#preset_colours").change(function() {
				prompt_colour.val(this.value).change();
			});
			var key_counter = 0;
			var prompt_text = $("#prompt_text").keyup(function() {
				prompt_category.val("");
				prompt_starter.val("");
				prompt_level.val("");
				key_counter++;
				if (key_counter == 10) {
					key_counter = 0;
					localStorage.setItem("prompt_colour", prompt_colour.val());
					localStorage.setItem("prompt_text", prompt_text.val());
					localStorage.setItem("prompt_category", prompt_category.val());
					localStorage.setItem("prompt_starter", prompt_starter.val());
					localStorage.setItem("prompt_level", prompt_level.val());
				}
			});
			var prompt_category = $("#prompt_category");
			var prompt_starter = $("#prompt_starter");
			var prompt_level = $("#prompt_level");

			var saved_new_or_saved_prompt = localStorage.getItem("new_or_saved_prompt");
			var saved_prompt_id = localStorage.getItem("prompt_id");
			var saved_prompt_colour = localStorage.getItem("prompt_colour");
			var saved_prompt_text = localStorage.getItem("prompt_text");
			var saved_prompt_category = localStorage.getItem("prompt_category");
			var saved_prompt_starter = localStorage.getItem("prompt_starter");
			var saved_prompt_level = localStorage.getItem("prompt_level");
			if (prompt_id.length > 0) {
				if (saved_new_or_saved_prompt) {
					$("#" + saved_new_or_saved_prompt).prop("checked", "checked").change();
				}
				if (saved_prompt_id) {
					prompt_id.val(saved_prompt_id);
				}
			}
			if (saved_prompt_colour && saved_prompt_text) {
				prompt_colour.val(saved_prompt_colour).change();
				prompt_text.text(saved_prompt_text);
			}
			if (saved_prompt_category) {
				prompt_category.val(saved_prompt_category);
			}
			if (saved_prompt_starter) {
				prompt_starter.val(saved_prompt_starter);
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
				if (last_mode=="prompt_mode" && autoprompt && saved_prompt_colour && saved_prompt_text && saved_prompt_category && saved_prompt_starter && saved_prompt_level) {
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
					prompt_data = {};
					for (var i=0; i<message.prompts.length; i++) {
						render_prompt(message.prompts[i]);
					}
				} else if (message.action=="new_prompt") {
					render_prompt(message);
				} else if (message.action=="remove_prompt") {
					delete prompt_data[message.id];
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
		"prompt_form": function() {
			var prompt_colour = $("#prompt_colour").change(function() {
				prompt_text.css("color", this.value);
			});
			var preset_colours = $("#preset_colours").change(function() {
				prompt_colour.val(this.value).change();
			});
		},
		"directory": function() {

			var search_input = $("#directory_search").keydown(function(e) {
				clearTimeout(autocomplete_timeout);
				if (e.which == 13 || e.which == 188) { // Enter and comma
					var current_autocomplete = autocomplete_list.find(".current");
					if (current_autocomplete.length > 0) {
						location.href = current_autocomplete.find("a").attr("href");
						return false;
					} else {
						return true;
					}
					return false;
				} else if (e.which == 38 || e.which == 40) { // Up and down
					var current_autocomplete = autocomplete_list.find(".current");
					if (current_autocomplete.length > 0) {
						current_autocomplete.removeClass("current");
						var new_current = e.which == 38 ? current_autocomplete.prev() : current_autocomplete.next();
						new_current.addClass("current");
					} else {
						autocomplete_list.find(e.which == 38 ? "li:last-child" : "li:first-child").addClass("current");
					}
				}
				autocomplete_timeout = setTimeout(load_autocomplete, 100);
			}).focus(function(e) {
				focussed = true;
				autocomplete_list.css("display", "");
				autocomplete_timeout = setTimeout(load_autocomplete, 100);
			}).blur(function(e) {
				focussed = false;
				if (!focussed && !hovered) {
					autocomplete_list.css("display", "none");
					clearTimeout(autocomplete_timeout);
				}
			});
			var search_div = search_input.parent()

			var autocomplete_list = $("<ul>").addClass("autocomplete_list").mouseenter(function(e) {
				hovered = true;
			}).mouseleave(function(e) {
				hovered = false;
				if (!focussed && !hovered) {
					search_input.focus();
				}
			}).insertAfter(search_div);

			var autocomplete_timeout;
			var last_autocomplete;
			var focused = false;
			var hovered = false;
			var active_request = null;

			function load_autocomplete() {

				if (search_input.val() == last_autocomplete) { return; }
				last_autocomplete = search_input.val();

				if (search_input.val().length < 3) { autocomplete_list.empty(); return; }

				if (active_request) { active_request.abort(); }
				active_request = $.get("/directory/search/autocomplete/", {"name": search_input.val()}, function(data) {
					autocomplete_list.empty();
					data.forEach(function(tag) {
						var li = $("<li>").hover(function() {
							autocomplete_list.find(".current").removeClass("current");
							$(this).addClass("current");
						});
						var a = $("<a>").attr("href", "/directory/" + tag.type + ":" + tag.url_name + "/")
						$("<div>").attr("class", "search_type").text(tag.type.replace(/_/g, " ")).appendTo(a);
						$("<div>").attr("class", "search_name").text(tag.name).appendTo(a);
						a.appendTo(li);
						li.appendTo(autocomplete_list);
					});
				});

			}

		},
		"directory_new": function() {
			var add_tag_functions = [];

			$("#new_request_form .tag_input").each(function() {

				var tag_list = $(this).find(".request_tags");

				var hidden_input = $(this).find("input");
				hidden_input.css("display", "none");

				var tag_type = hidden_input.attr("name");

				var visible_input = $("<input>").keydown(function(e) {
					if (e.which == 13 || e.which == 188) { // Enter and comma
						add_tag();
						return false;
					} else if (e.which == 8 && !visible_input.val()) { // Backspace
						remove_tag();
					} else if (e.which == 38 || e.which == 40) { // Up and down
						var current_autocomplete = autocomplete_list.find(".current");
						if (current_autocomplete.length > 0) {
							current_autocomplete.removeClass("current");
							var new_current = e.which == 38 ? current_autocomplete.prev() : current_autocomplete.next();
							new_current.addClass("current");
						} else {
							autocomplete_list.find(e.which == 38 ? "li:last-child" : "li:first-child").addClass("current");
						}
					}
					clearTimeout(autocomplete_timeout);
					autocomplete_timeout = setTimeout(load_autocomplete, 100);
				}).focus(function(e) {
					autocomplete_list.css("display", "");
					autocomplete_timeout = setTimeout(load_autocomplete, 100);
				}).blur(function(e) {
					autocomplete_list.css("display", "none");
					autocomplete_list.find(".current").removeClass("current");
					clearTimeout(autocomplete_timeout);
				}).addClass("full").attr({
					"type": "text",
					"maxlength": hidden_input.attr("maxlength"),
					"placeholder": hidden_input.attr("placeholder"),
				}).appendTo(this);

				var autocomplete_list = $("<ul>").addClass("autocomplete_list").insertAfter(this);
				var autocomplete_timeout;
				var last_autocomplete;

				function refresh_hidden_input() {
					hidden_input.val(tag_list.find("a").map(function(index, tag) { return $(tag).attr("data-tag-name"); }).toArray().join(","));
				}

				function add_tag() {
					var current_autocomplete = autocomplete_list.find(".current");
					if (current_autocomplete.length > 0) {
						make_tag_list(current_autocomplete.text());
						autocomplete_list.empty();
					} else {
						make_tag_list(visible_input.val());
					}
					visible_input.val("");
					refresh_hidden_input();
				}
				// Remember these so we can run them on submit.
				add_tag_functions.push(add_tag)

				function remove_tag() {
					tag_list.find("li:last-child").remove();
					refresh_hidden_input();
				}

				function make_tag_list(value) {
					value.split(",").forEach(function(tag_name) {

						tag_name = tag_name.trim();
						if (tag_type == "warning") { tag_name = tag_name.replace(/^tw:\s*/gi, ""); }
						if (!tag_name) { return; }

						var existing_tags = tag_list.find("a");
						for (var i = 0; i < existing_tags.length; i++) {
							if ($(existing_tags[i]).attr("data-tag-name").toLowerCase() == tag_name.toLowerCase()) {
								$(existing_tags[i].parentNode).appendTo(tag_list);
								return;
							}
						}

						var li = $("<li>").text(" ");
						if (tag_type == "warning") { li.addClass("warning"); }
						li.appendTo(tag_list);
						$("<a>").attr({
							"href": "#",
							"data-tag-name": tag_name,
						}).click(function() {
							$(this.parentNode).remove();
							refresh_hidden_input();
							return false;
						}).text(tag_name).appendTo(li);

					});
				}

				var active_request = null;

				function load_autocomplete() {

					if (visible_input.val() == last_autocomplete) { return; }
					last_autocomplete = visible_input.val();

					if (visible_input.val().length < 3) { autocomplete_list.empty(); return; }

					if (active_request) { active_request.abort(); }
					active_request = $.get("/directory/new/autocomplete/", {"type": tag_type, "name": visible_input.val()}, function(data) {
						autocomplete_list.empty();
						for(i=0; i<data.length; i++) {
							$("<li>").text(data[i]).hover(function() {
								autocomplete_list.find(".current").removeClass("current");
								$(this).addClass("current");
							}).mousedown(function() {
								if (!$(this).hasClass("current")) {
									autocomplete_list.find(".current").removeClass("current");
									$(this).addClass("current");
								}
								add_tag();
							}).appendTo(autocomplete_list);
						}
					});

				}

				make_tag_list(hidden_input.val());

			});

			var prompt_colour = $("#new_request_form input[name=\"colour\"]").change(function() {
				$("#new_request_form textarea[name=\"prompt\"]").css("color", this.value);
			});
			var preset_colours = $("#new_request_form select[name=\"preset_colours\"]").change(function() {
				prompt_colour.val(this.value).change();
			});

			$("#new_request_form").submit(function() {
				add_tag_functions.forEach(function(func) { func(); });
			});

			var group_slots = $("#group_slots");
			var required_slots = $(".required_slot");
			$("input[name=mode]").change(function() {
				if (this.checked) {
					if (this.value == "group") {
						group_slots.css("display", "block");
						required_slots.attr("required", "required");
					} else {
						group_slots.css("display", "none");
						required_slots.removeAttr("required");
					}
				}
			}).change();

		},
		"directory_blacklist": function() {
			var maturity_name = $("#blacklist_add select[name=maturity_name]");
			var type_name = $("#blacklist_add select[name=type_name]");
			var other_name = $("#blacklist_add input[name=name]");
			$("#blacklist_add select[name=tag_type]").change(function() {
				if (this.value == "maturity") {
					maturity_name.show();
					type_name.hide();
					other_name.hide().val("").removeAttr("required");
				} else if (this.value == "type") {
					maturity_name.hide();
					type_name.show();
					other_name.hide().val("").removeAttr("required");
				} else {
					maturity_name.hide();
					type_name.hide();
					other_name.show().attr("required", "required");
				}
			}).change();
		},
		"account": function(application_server_key) {
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
			var enter_to_send = $("#enter_to_send").click(function() {
				localStorage.setItem("enter_to_send", this.checked);
				if (this.checked) {
					$("#confirmation").text("Pressing enter to send is now enabled.");
				} else {
					$("#confirmation").text("Pressing enter to send is now disabled.");
				}
				window.scroll(0, 0);
			});
			if (localStorage.getItem("enter_to_send") == "true") {
				enter_to_send.attr("checked", "checked");
			}
			var cross_chat_notifications = $("#cross_chat_notifications").click(function() {
				localStorage.setItem("cross_chat_notifications", this.checked);
				if (this.checked) {
					$("#confirmation").text("Notifications from other chats are now enabled.");
				} else {
					$("#confirmation").text("Notifications from other chats are now disabled.");
				}
				window.scroll(0, 0);
			});
			if (localStorage.getItem("cross_chat_notifications") == "true") {
				cross_chat_notifications.attr("checked", "checked");
			}

			var push_notifications_unsupported = $("#push_notifications_unsupported");
			var push_notifications_disabled    = $("#push_notifications_disabled");
			var push_notifications_denied      = $("#push_notifications_denied");
			var push_notifications_enabled     = $("#push_notifications_enabled");

			if (!("serviceWorker" in navigator)) {
				return false;
			}
			navigator.serviceWorker.register("/static/cherubplay_sw.js", {"scope": "/"}).then(function(reg) {
				window.reg = reg;
				if (!(reg.showNotification) || !("PushManager" in window)) {
					return false;
				}
				if (Notification.permission === "denied") {
					push_notifications_denied.show();
				}
				navigator.serviceWorker.ready.then(function(reg) {
					reg.pushManager.getSubscription().then(function(subscription) {
						push_notifications_unsupported.hide();
						if (subscription) {
							push_notifications_enabled.show();
						} else {
							push_notifications_disabled.show();
						}
					});
					$("#enable_push_notifications").click(function() {
						reg.pushManager.getSubscription().then(function(subscription) {
							if (!subscription) {
								reg.pushManager.subscribe({
										userVisibleOnly: true,
										applicationServerKey: urlBase64ToUint8Array(application_server_key),
									}).then(function(subscription) {
									$.post("/account/push/subscribe/", {"subscription": JSON.stringify(subscription.toJSON())});
									push_notifications_enabled.show();
									push_notifications_denied.hide();
									push_notifications_disabled.hide();
								});
							}
						});
					});
					$("#disable_push_notifications").click(function() {
						reg.pushManager.getSubscription().then(function(subscription) {
							if (subscription) {
								subscription.unsubscribe().then(function() {
									$.post("/account/push/unsubscribe/", {"subscription": JSON.stringify(subscription.toJSON())});
									push_notifications_enabled.hide();
									push_notifications_disabled.show();
								});
							}
						});
					});
				});
			});

		},
		"chat": function(chat_url, own_handle) {

			var latest_message_id;
			var messages = $("#messages li");
			if (messages && messages.length > 0) {
				latest_message_id = parseInt(messages[messages.length-1].id.substr(8));
			}

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
				if (body.hasClass("layout2")) {
					var jquery_this = $(this.parentNode.parentNode);
				} else {
					var jquery_this = $(this);
				}
				var editing_this = jquery_this.hasClass("editing");
				if (editing_this) {
					cancel_editing();
				} else {
					$(".editing .edit_link").text("Edit");
					$(".editing").removeClass("editing");
					if (!editing_id) {
						pre_edit_color = message_colour.val();
						pre_edit_ooc = message_ooc[0].checked;
						pre_edit_text = message_text.val();
					}
					editing_id = jquery_this.attr("id").substr(8);
					message_form.attr("action", "/chats/"+chat_url+"/edit/"+editing_id+"/");
					jquery_this.addClass("editing");
					if (body.hasClass("layout2")) {
						this.innerHTML = "Stop editing";
					}
					message_form_container.addClass("editing");
					var paragraph = jquery_this.find("p");
					message_colour.val(paragraph.css("color")).change();
					message_ooc[0].checked = jquery_this.hasClass("message_ooc");
					var edit_text = body.hasClass("layout2") ? paragraph.text() : paragraph.text().substr(3);
					message_text.css("height", "100px").val(edit_text).keyup();
					message_form.find("button").text("Edit");
					window.scrollTo(0, message_form_container.position()["top"]-50);
					message_text.focus();
				}
				return false;
			}

			function cancel_editing() {
				$(".editing .edit_link").text("Edit");
				$(".editing").removeClass("editing");
				editing_id = null;
				message_form.attr("action", "/chats/"+chat_url+"/send/");
				message_colour.val(pre_edit_color).change();
				message_ooc[0].checked = pre_edit_ooc;
				message_text.css("height", "100px").val(pre_edit_text).change().keyup();
				message_form.find("button").text("Send");
				window.scrollTo(0, message_form_container.position()["top"]-50);
			}

			if (body.hasClass("layout2")) {
				$(".edit_link").click(start_editing);
			} else {
				$("#messages li[data-handle=" + own_handle + "]").dblclick(start_editing);
			}

			var status_bar = $("#status_bar");
			var last_status_message = status_bar.text().trim() || "Connected.";

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
				message_symbol.css("color", this.value);
			});
			var preset_colours = $("#preset_colours").change(function() {
				message_colour.val(this.value).change();
			});
			var message_ooc = $("#message_ooc");
			var message_symbol = $("#message_form .symbol");
			var message_text = $("#message_text").keypress(function(e) {
				changed_since_draft = true;
				if (enter_to_send && e.keyCode==13 && !e.shiftKey) {
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
			});

			var search_again = $("#search_again").click(function() {
				localStorage.setItem("autoprompt", "yes");
			});

			var user_list_entries = {};
			$("#chat_user_list [data-handle]").each(function(index, item) {
				user_list_entries[item.dataset.handle] = item;
			});

			var notification_audio;
			function play_notification_audio() {
				if (localStorage.getItem("sound_notifications") == "true") {
					if (!notification_audio) {
						var notification_audio = $("<audio autoplay>");
						$("<source>").attr("src", "/static/carne_vale.ogg").appendTo(notification_audio);
						$("<source>").attr("src", "/static/carne_vale.mp3").appendTo(notification_audio);
					}
					notification_audio[0].play();
				}
			}

			$("#notification_close").click(function() {
				$("#notification").hide();
			});

			var enter_to_send = localStorage.getItem("enter_to_send") == "true";

			var changed_since_draft = false;
			function save_draft() {
				if (!editing_id && changed_since_draft) {
					$.post("/chats/" + chat_url + "/draft/", {message_text: message_text.val().trim()});
				}
				changed_since_draft = false;
			}
			window.setInterval(save_draft, 15000);

			function ping() {
				if (ws.readyState==1) {
					ws.send('{"action":"ping"}');
					window.setTimeout(ping, 8000);
				}
			}

			function render_message(message) {
				latest_message_id = Math.max(latest_message_id, message.id);
				// Check if we're at the bottom before rendering because rendering will mean that we're not.
				var scroll_after_render = is_at_bottom();
				var message_handle = (message.symbol || message.name);
				if (body.hasClass("layout2")) {
					var li = $("<li>").attr("id", "message_" + message.id).addClass("message_" + message.type).css("color", "#" + message.colour);
					var timestamp = $("<div>").addClass("timestamp");
					if (message.name) {
						timestamp.text(message.name + " · ");
					}
					timestamp.text(timestamp.text() + new Date().toLocaleString());
					if (message_handle) {
						li.attr("data-handle", message_handle);
						if (message_handle == own_handle) {
							timestamp.text(timestamp.text() + " · ");
							$("<a>").attr("href", "#").addClass("edit_link").text("Edit").click(start_editing).appendTo(timestamp);
						}
					}
					if (message.symbol) {
						$("<span>").addClass("symbol").text(message.symbol).appendTo(li);
					}
					if (message_handle && message.type == "system") {
						var text = message.text.replace("%s", message_handle);
					} else {
						var text = message.text;
					}
					$("<p>").text(text).appendTo(li);
					timestamp.appendTo(li);
					li.appendTo(messages);
				} else {
					var li = $("<li>").attr("id", "message_"+message.id).addClass("tile message_"+message.type);
					if (message.symbol) {
						li.attr("data-symbol", message.symbol);
						if (message.symbol == own_handle) {
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
				}
				if (scroll_after_render) {
					scroll_to_bottom();
				}
				if (document.hidden || document.webkitHidden || document.msHidden) {
					document.title = "New message - " + original_title;
					play_notification_audio();
				}
			}

			if (typeof WebSocket!="undefined") {
				var ws;
				var ws_works = false;
				var ws_connected_time = 0;
				function launch_websocket() {
					var ws_protocol = location.protocol == "https:" ? "wss://" : "ws://";
					var after = latest_message_id ? "?after=" + latest_message_id : ""
					ws = new WebSocket(ws_protocol + location.host + "/live/" + chat_url + "/" + after);
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
						play_notification_audio();
					}
					if (user_list_entries[own_handle]) {
						user_list_entries[own_handle].classList.add("online");
					}
				}
				function ws_onmessage(e) {
					if (!ended) {
						message = JSON.parse(e.data);
						if (message.action == "message") {
							render_message(message.message);
							if (!body.hasClass("layout2")) {
								last_status_message = "Last message: " + new Date().toLocaleString();
							}
							status_bar.text(last_status_message);
							if (message.message.name && user_list_entries && user_list_entries[message.message.name]) {
								user_list_entries[message.message.name].style.color = "#" + message.message.colour;
							}
						} else if (message.action == "edit") {
							status_bar.text(last_status_message);
							var li = $("#message_"+message.message.id);
							if (li.length == 0) {
								return;
							}
							li.removeClass("message_ic").removeClass("message_ooc").addClass("message_"+message.message.type);
							if (message.message.show_edited) {
								li.addClass("edited");
							}
							var p = li.find("p")
							if (body.hasClass("layout2")) {
								li.css("color", "#"+message.message.colour);
								p.text(message.message.text);
							} else {
								p.css("color", "#"+message.message.colour).text(message.message.symbol+": "+message.message.text);
							}
						} else if (message.action == "end") {
							$(body).removeClass("ongoing");
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
									status_bar.hide();
								});
							} else {
								status_bar.hide();
							}
							message_form_container.remove();
							render_message(message.message);
						} else if (message.action == "typing") {
							if (message.handle != own_handle) {
								status_bar.text(message.handle + " is typing.");
							}
						} else if (message.action == "stopped_typing") {
							status_bar.text(last_status_message);
						} else if (message.action == "online") {
							last_status_message = message.handle + " is online.";
							status_bar.text(last_status_message);
							user_list_entries[message.handle].classList.add("online");
						} else if (message.action == "online_list") {
							last_status_message = "Online: " + message.handles.join(", ");
							status_bar.text(last_status_message);
							for (var handle of message.handles) {
								if (user_list_entries[handle]) {
									user_list_entries[handle].classList.add("online");
								}
							}
						} else if (message.action == "offline") {
							last_status_message = message.handle + " is now offline. They will be notified of any messages you send when they next visit.";
							status_bar.text(last_status_message);
							user_list_entries[message.handle].classList.remove("online");
						} else if (
							body.hasClass("layout2")
							&& window.innerWidth > 1024
							&& message.action == "notification"
							&& localStorage.getItem("cross_chat_notifications") == "true"
						) {
							$("#notification").show();
							$("#notification_title").attr("href", "https://" + location.host + "/chats/" + message.url + "/").text(message.title);
							if (message.symbol) {
								$("#notification_symbol").css("color", "#" + message.colour).text(message.symbol);
							}
							$("#notification_text").css("color", "#" + message.colour).text(message.text);
						}
					}
				}
				function ws_onclose(e) {
					if (user_list_entries[own_handle]) {
						user_list_entries[own_handle].classList.remove("online");
					}
					if (ended) { return; }
					status_bar.text("Live updates currently unavailable. Please refresh to see new messages.");
					// Only try to re-connect if we've managed to connect before.
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

