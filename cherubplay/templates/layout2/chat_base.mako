<%inherit file="base.mako" />\
<%block name="title">
% if own_chat_user:
${own_chat_user.title or chat.url} - 
% endif
</%block>
<%block name="body_class">layout2</%block>
<%def name="render_message(message, show_edit=False)">\
      <li id="message_${message.id}" class="message_${message.type}${" edited" if message.show_edited() else ""}" data-symbol="${message.symbol_character if message.symbol is not None else ""}" style="color: #${message.colour};">
% if message.symbol is not None:
        <span class="symbol">${message.symbol_character}</span>
% endif
% if message.symbol is not None and message.type=="system":
        <p>${message.text % message.symbol_character}</p>
% else:
        <p>${message.text}</p>
% endif
        <div class="timestamp">${(request.user.localise_time(message.posted) if request.user is not None else message.posted).strftime("%Y-%m-%d %H:%M:%S")}\
% if show_edit and own_chat_user.user_id == message.user_id:
 · <a href="#" class="edit_link">Edit</a>\
% endif
</div>
      </li>
</%def>\
% if own_chat_user:
<h2>${own_chat_user.title or chat.url}</h2>
% endif
<main class="flex">
% if own_chat_user:
  <div class="side_column">
    <nav>
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
    </nav>
  </div>
  <div class="side_column">
    <nav>
      <form action="${request.route_path("account_layout_version")}" method="post">
        <input type="hidden" name="layout_version" value="1">
        <p>This is the new layout. <button type="submit">Return to the old layout</button></p>
      </form>
    </nav>
  </div>
% endif
  <div id="content">
% if symbol_users:
    <section class="tile2">
      <h3>Users</h3>
      <ul>
% for symbol, user in symbol_users.items():
        <li>${symbol} is #${user.id} <a href="${request.route_path("admin_user", username=user.username)}">${user.username}</a> (${user.status}).</li>
% endfor
      </ul>
    </section>
% endif
${next.body()}\
  </div>
</main>
