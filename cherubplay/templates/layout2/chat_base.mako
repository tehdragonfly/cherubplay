<%inherit file="base.mako" />\
<% from cherubplay.models.enums import ChatMode %>
<% from cherubplay.lib import symbols %>
<%block name="title">
% if request.context.chat_user:
${request.context.chat_user.display_title} -
% endif
</%block>
<%block name="body_class">layout2</%block>
<%def name="render_message(chat, user, chat_user, message, show_edit=False)">\
      <li id="message_${message.id}" class="message_${message.type.value}${" edited" if message.show_edited else ""}" data-handle="${message.handle or ""}" style="color: #${message.colour};" data-raw="${message.text.raw}">
        ${render_message_inner(chat, user, chat_user, message, show_edit)}
      </li>
</%def>\
<%def name="render_message_inner(chat, user, chat_user, message, show_edit=False)">\
<% from cherubplay.models.enums import ChatMode, MessageType %>\
% if message.symbol is not None:
        <span class="symbol">${message.symbol_character}</span>
% endif
% if message.symbol is not None and message.type == MessageType.system:
        <p>${message.text.as_plain_text() % message.symbol_character}</p>
% else:
        ${message.text.as_html()}
% endif
        <div class="timestamp">
          % if chat.mode == ChatMode.group and message.handle:
            ${message.handle} ·
          % endif
          ${(user.localise_time(message.posted) if user is not None else message.posted).strftime("%Y-%m-%d %H:%M:%S")}
          % if show_edit and chat_user.user_id == message.user_id:
            · <a href="#" class="edit_link">Edit</a>\
          % endif
        </div>
</%def>\
% if request.context.chat_user:
  <h2>${request.context.chat_user.display_title}</h2>
% endif
<main class="flex">
  <div class="side_column">
    <nav>
      % if request.context.chat_user:
        <ul>
          % if request.context.chat.status == "ongoing":
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
          % if page == "export":
            <li>Export</li>
          % else:
            <li><a href="${request.route_path("chat_export", url=request.matchdict["url"])}">Export</a></li>
          % endif
        </ul>
      % endif
    </nav>
  </div>
  <div class="side_column">
    <nav>
      % if page in ("chat", "archive") and request.context.chat.mode == ChatMode.group:
        <h3>Users</h3>
        <ul id="chat_user_list">
          % if request.has_permission("chat.full_user_list"):
            % for user_id, chat_user in request.context.chat_users.items():
              <li class="${chat_user.status.value if request.context.chat.status == "ongoing" else ""}">
                <a href="${request.route_path("admin_user", username=chat_user.user.username)}" class="user_list_bullet" style="color: #${chat_user.last_colour}" data-handle="${chat_user.name}">
                  ${chat_user.name} (#${chat_user.user.id}&nbsp;${chat_user.user.username})
                </a>
              </li>
            % endfor
          % else:
            % for user_id, chat_user in request.context.chat_users.items():
              <li class="user_list_bullet ${chat_user.status.value if request.context.chat.status == "ongoing" else ""}" style="color: #${chat_user.last_colour}" data-handle="${chat_user.name}">
                ${chat_user.name}
                % if chat_user in request.context.banned_chat_users:
                  (${"temporarily" if chat_user.user.unban_date else "permanently"} banned)
                % elif chat_user in request.context.away_chat_users:
                  (away)
                % endif
              </li>
            % endfor
          % endif
        </ul>
      % endif
      % if page == "archive":
        <ul>
          % if "hide_ooc" in request.GET:
            <li><a href="${request.route_path("chat", url=request.matchdict["url"], _query={"page": 1})}">Show OOC</a></li>
            <li>Hide OOC</li>
          % else:
            <li>Show OOC</li>
            <li><a href="${request.route_path("chat", url=request.matchdict["url"], _query={"page": 1, "hide_ooc": "true"})}">Hide OOC</a></li>
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
