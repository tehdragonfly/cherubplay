<%inherit file="base.mako" />\
<% from cherubplay.lib import symbols %>
<%block name="title">
% if own_chat_user:
${own_chat_user.title or chat.url} - 
% endif
</%block>
<%block name="body_class">layout2</%block>
<%def name="render_message(message, show_edit=False)">\
      <li id="message_${message.id}" class="message_${message.type}${" edited" if message.show_edited else ""}" data-handle="${message.handle or ""}" style="color: #${message.colour};">
% if message.symbol is not None:
        <span class="symbol">${message.symbol_character}</span>
% endif
% if message.symbol is not None and message.type == "system":
        <p>${message.text % message.symbol_character}</p>
% else:
        <p>${message.text}</p>
% endif
        <div class="timestamp">
          % if request.context.mode == "group" and message.handle:
            ${message.handle} ·
          % endif
          ${(request.user.localise_time(message.posted) if request.user is not None else message.posted).strftime("%Y-%m-%d %H:%M:%S")}
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
  <div class="side_column">
    <nav>
      % if own_chat_user:
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
      % endif
    </nav>
  </div>
  <div class="side_column">
    <nav>
      % if own_chat_user and request.context.mode != "group":
        <form action="${request.route_path("account_layout_version")}" method="post">
          <input type="hidden" name="layout_version" value="1">
          <p>This is the new layout. <button type="submit">Return to the old layout</button></p>
        </form>
      % endif
      % if page in ("chat", "archive") and request.context.mode == "group":
        <h3>Users</h3>
        <ul id="chat_user_list">
          % if request.has_permission("chat.full_user_list"):
            % for user_id, chat_user in request.context.chat_users.items():
              <li class="${chat_user.status.value if request.context.chat.status == "ongoing" else ""}">
                <a href="${request.route_path("admin_user", username=chat_user.user.username)}" style="color: #${chat_user.last_colour}" data-handle="${chat_user.name}">
                  ${chat_user.name}
                </a>
              </li>
            % endfor
          % else:
            % for user_id, chat_user in request.context.chat_users.items():
              <li class="${chat_user.status.value if request.context.chat.status == "ongoing" else ""}" style="color: #${chat_user.last_colour}" data-handle="${chat_user.name}">
                ${chat_user.name}
              </li>
            % endfor
          % endif
        </ul>
      % endif
    </nav>
  </div>
  <div id="content">
    % if symbol_users:
      <section class="tile2">
        <h3>Users</h3>
        <ul>
          % for symbol, user in sorted(symbol_users.items(), key=lambda _: symbols.index(_[0])):
          <li>${symbol} is #${user.id} <a href="${request.route_path("admin_user", username=user.username)}">${user.username}</a> (${user.status}).</li>
          % endfor
        </ul>
      </section>
    % endif
${next.body()}\
  </div>
</main>
