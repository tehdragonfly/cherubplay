<%inherit file="base.mako" />\
% if symbol_users:
  <section class="tile">
    <h3>users</h3>
    <ul>
% for symbol, user in symbol_users.items():
      <li>${symbols[symbol]} is #${user.id} <strong>${user.username}</strong> (${user.status}).</li>
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
last message: ${messages[-1].posted}.\
% endif
</section>
  <section id="message_form_container" class="tile">
    <form id="message_form" action="${request.route_path("chat_send", url=request.matchdict["url"])}" method="post">
      <p><input type="color" id="message_colour" name="message_colour" size="6" value="#${own_chat_user.last_colour}"> <select id="preset_colours" name="preset_colours">
% for hex, name in preset_colours:
          <option value="#${hex}">${name}</option>
% endfor
        </select><label title="only lame chumps like john tick this"><input type="checkbox"name="message_ooc"> unironic mode</label></p>
      <p><textarea id="message_text" name="message_text" placeholder="write a message" style="color: #${own_chat_user.last_colour}"></textarea></p>
      <button type="submit" id="send_button">send</button>
    </form>
    <form id="end_form" action="${request.route_path("chat_end", url=request.matchdict["url"])}" method="post">
% if from_homepage:
		<label id="continue_search_label"><input type="checkbox" id="continue_search" name="continue_search" checked="checked"> search again</label>
% endif
		<button type="submit">end chat</button>
	</form>
  </section>
% endif
<%block name="scripts">
% if continuable:
<script>cherubplay.chat("${request.matchdict["url"]}");</script>
% endif
</%block>
