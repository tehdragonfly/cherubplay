<%inherit file="base.mako" />\
<%def name="render_message(message)">\
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
</%def>\
% if symbol_users:
  <section class="tile">
    <h3>Users</h3>
    <ul>
% for symbol, user in symbol_users.items():
      <li>${symbols[symbol]} is #${user.id} <strong>${user.username}</strong> (${user.status}).</li>
% endfor
    </ul>
  </section>
% endif
  <ul id="messages">
% if prompt:
${render_message(prompt)}
    <li class="tile pager"><a href="${request.route_path("chat", url=request.matchdict["url"], _query={ "page": 1 })}">${message_count-10} more messages</a></li>
% endif
% for message in messages:
${render_message(message)}\
% endfor
  </ul>
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
        </select><label title="Talk out of character; use ((double brackets)) to automatically OOC."><input type="checkbox" name="message_ooc"> OOC</label></p>
      <p><textarea id="message_text" name="message_text" placeholder="Write a message..." style="color: #${own_chat_user.last_colour}"></textarea></p>
      <button type="submit" id="send_button">Send</button>
    </form>
    <p id="info_link"><a href="${request.route_path("chat_info", url=request.matchdict["url"])}">Edit chat info</a>\
% if from_homepage:
 · <a href="${request.route_path("home", url=request.matchdict["url"])}" id="search_again">Search again</a>\
% endif
</p>
  </section>
<%block name="scripts">
<script>cherubplay.chat("${request.matchdict["url"]}");</script>
</%block>
