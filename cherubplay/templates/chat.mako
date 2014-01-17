<%inherit file="base.mako" />\
% if chat_users:
  <section class="tile">
    <h3>Users</h3>
    <ul>
% for chat_user in chat_users:
      <li>${symbols[chat_user.symbol]} is <strong>${chat_user.user.username}</strong>.</li>
% endfor
    </ul>
  </section>
% endif
  <ul id="messages">
% for message in messages:
    <li class="tile message_${message.type}">
% if message.symbol is not None:
% if message.type=="system":
      <p style="color: #${message.colour};">${message.text % symbols[message.symbol]}</p>
% else:
      <p style="color: #${message.colour};">${symbols[message.symbol]}: ${message.text}</p>
% endif
% else:
      <p style="color: #${message.colour};">${message.text}</p>
% endif
    </li>
% endfor
  </ul>
% if continuable:
  <section id="status_bar">\
% if len(messages)>0:
Last message: ${messages[-1].posted}.\
% endif
</section>
  <section id="message_form_container" class="tile">
    <form id="message_form" action="${request.route_path("chat_send", url=request.matchdict["url"])}" method="post">
      <p><input type="color" id="message_colour" name="message_colour" size="6" value="#${own_chat_user.last_colour}"> <select id="preset_colours" name="preset_colours">
% for hex, name in preset_colours:
          <option value="#${hex}">${name}</option>
% endfor
        </select><label title="Talk out of character; use ((double brackets)) to automatically OOC."><input type="checkbox"name="message_ooc"> OOC</label></p>
      <p><textarea id="message_text" name="message_text" placeholder="Write a message..." style="color: #${own_chat_user.last_colour}"></textarea></p>
      <button type="submit" id="send_button">Send</button>
    </form>
    <form id="end_form" action="${request.route_path("chat_end", url=request.matchdict["url"])}" method="post">
% if from_homepage:
		<label id="continue_search_label"><input type="checkbox" id="continue_search" name="continue_search" checked="checked"> Search again</label>
% endif
		<button type="submit">End chat</button>
	</form>
  </section>
  <script>var chat_url = "${request.matchdict["url"]}";</script>
  <script src="http://code.jquery.com/jquery-2.0.3.min.js"></script>
  <script src="/static/chat.js?3"></script>
% endif
