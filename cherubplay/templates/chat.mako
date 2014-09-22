<%inherit file="base.mako" />\
<%def name="render_message(message)">\
    <li id="message_${message.id}" class="tile message_${message.type}"\
% if message.symbol is not None:
 data-symbol="${symbols[message.symbol]}">
% if message.type=="system":
      <p style="color: #${message.colour};">${message.text % symbols[message.symbol]}</p>
% else:
      <p style="color: #${message.colour};">${symbols[message.symbol]}: ${message.text}</p>
% endif
% else:
>
      <p style="color: #${message.colour};">${message.text}</p>
% endif
    </li>
</%def>\
<%def name="user_list(symbol_users)">\
  <section class="tile">
    <h3>Users</h3>
    <ul>
% for symbol, user in symbol_users.items():
      <li>${symbols[symbol]} is #${user.id} <a href="${request.route_path("admin_user", username=user.username)}">${user.username}</a> (${user.status}).</li>
% endfor
    </ul>
  </section>
</%def>\
<%def name="render_subnav(page, chat, own_chat_user)">\
  <h2>${own_chat_user.title or chat.url}</h2>
  <nav id="subnav">
    <section class="tile">
      <ul>
% if chat.status == "ongoing":
% if page == "chat":
        <li>Chat</li>
% else:
        <li><a href="${request.route_path("chat", url=request.matchdict["url"])}">Chat</a></li>
% endif
% endif
% if page == "archive":
        <li>Archive</li>
% else:
        <li><a href="${request.route_path("chat", url=request.matchdict["url"], _query={ "page": 1 })}">Archive</a></li>
% endif
% if page == "info":
        <li>Info</li>
% else:
        <li><a href="${request.route_path("chat_info", url=request.matchdict["url"])}">Info</a></li>
% endif
      </ul>
    </section>
  </nav>
</%def>\
${render_subnav("chat", chat, own_chat_user)}
% if symbol_users:
${user_list(symbol_users)}
% endif
  <ul id="messages">
% if prompt:
${render_message(prompt)}
    <li class="tile pager"><a href="${request.route_path("chat", url=request.matchdict["url"], _query={ "page": 1 })}">${message_count-26} more messages</a></li>
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
        </select><label title="Talk out of character; use ((double brackets)) to automatically OOC."><input id="message_ooc" type="checkbox" name="message_ooc"> OOC</label></p>
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
<script>cherubplay.chat("${request.matchdict["url"]}", "${symbols[own_chat_user.symbol]}");</script>
</%block>
