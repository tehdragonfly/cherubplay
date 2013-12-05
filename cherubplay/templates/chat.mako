<%inherit file="base.mako" />\
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
      <p>
        <input type="color" id="message_colour" name="message_colour" size="6" value="#${own_chat_user.last_colour}">
        <select id="preset_colours" name="preset_colours">
% for hex, name in preset_colours:
          <option value="#${hex}">${name}</option>
% endfor
        </select>
      </p>
      <p><textarea id="message_text" name="message_text" placeholder="Write a message..." style="color: #${own_chat_user.last_colour}"></textarea></p>
      <button type="submit" id="send_button">Send</button>
    </form>
    <form id="end_form" action="${request.route_path("chat_end", url=request.matchdict["url"])}" method="post"><button type="submit">End chat</button></form>
  </section>
  <script>var chat_url = "${request.matchdict["url"]}";</script>
  <script src="http://code.jquery.com/jquery-2.0.3.min.js"></script>
  <script src="/static/chat.js"></script>
% endif