<%inherit file="base.mako" />\
<% from cherubplay.lib import preset_colours, symbols %>
<%block name="title">${request.context.chat_user.display_title} - </%block>
<%def name="render_message(message)">\
<% from cherubplay.models.enums import MessageType %>\
    <li id="message_${message.id}" class="tile message_${message.type.value}\
% if message.show_edited:
 edited\
% endif
"\
 style="color: #${message.colour};"\
 data-raw="${message.text.raw}"\
% if message.symbol is not None:
 data-symbol="${message.symbol_character}">
% if message.type == MessageType.system:
      <p style="color: #${message.colour};">${message.text.as_plain_text() % message.symbol_character}</p>
% else:
      <span class="symbol">${message.symbol_character}:&nbsp;</span>
      ${message.text.as_html()}
% endif
% else:
>
      ${message.text.as_html()}
% endif
    </li>
</%def>\
<%def name="user_list(symbol_users)">\
  <% from cherubplay.lib import symbols %>\
  <section class="tile">
    <h3>Users</h3>
    <ul>
% for symbol, user in sorted(symbol_users.items(), key=lambda _: symbols.index(_[0])):
      <li>${symbol} is #${user.id} <a href="${request.route_path("admin_user", username=user.username)}">${user.username}</a> (${user.status}).</li>
% endfor
    </ul>
  </section>
</%def>\
<%def name="render_subnav(page, chat, own_chat_user)">\
  <h2>${request.context.chat_user.display_title}</h2>
  <nav id="subnav">
    <section class="tile">
      <ul>
% if request.context.is_continuable:
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
        <li><a href="${request.route_path("chat_export", url=request.matchdict["url"])}">Export</a></li>
      </ul>
    </section>
    % if page == "archive":
      <section class="tile">
        <ul>
          % if "hide_ooc" in request.GET:
            <li><a href="${request.route_path("chat", url=request.matchdict["url"], _query={"page": 1})}">Show OOC</a></li>
            <li>Hide OOC</li>
          % else:
            <li>Show OOC</li>
            <li><a href="${request.route_path("chat", url=request.matchdict["url"], _query={"page": 1, "hide_ooc": "true"})}">Hide OOC</a></li>
          % endif
        </ul>
      </section>
    % endif
    <form action="${request.route_path("account_layout_version")}" method="post">
      <input type="hidden" name="layout_version" value="2">
      <section class="tile">
        <p>This is the old layout. <button type="submit">Try the new layout</button></p>
      </section>
    </form>
  </nav>
</%def>\
${render_subnav("chat", request.context.chat, request.context.chat_user)}
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
% for banned_chat_user in request.context.banned_chat_users:
    <li class="tile message_system"><p><i>${banned_chat_user.handle}</i> has been ${"temporarily" if banned_chat_user.user.unban_date else "permanently"} banned from Cherubplay.</p></li>
% endfor
% for away_chat_user in request.context.away_chat_users:
% if away_chat_user not in request.context.banned_chat_users and away_chat_user != request.context.chat_user:
    <li class="tile message_system"><p><i>${away_chat_user.handle}</i> has marked their account as away. They left this message:

${away_chat_user.user.away_message}</p></li>
% endif
% endfor
  </ul>
  <section id="status_bar">\
% if len(messages)>0:
Last message: ${request.user.localise_time(messages[-1].posted).strftime("%Y-%m-%d %H:%M:%S")}.\
% endif
</section>
  <section id="message_form_container" class="tile">
    <form id="message_form" action="${request.route_path("chat_send", url=request.matchdict["url"])}" method="post">
      <p><input type="color" id="message_colour" name="message_colour" size="6" value="#${request.context.chat_user.last_colour}"> <select id="preset_colours" name="preset_colours">
% for hex, name in preset_colours:
          <option value="#${hex}">${name}</option>
% endfor
        </select><label title="Talk out of character; use ((double brackets)) to automatically OOC."><input id="message_ooc" type="checkbox" name="message_ooc"> OOC</label></p>
      <p><textarea id="message_text" name="message_text" placeholder="Write a message..." style="color: #${request.context.chat_user.last_colour}">${request.context.chat_user.draft}</textarea></p>
      <button type="submit" id="send_button">Send</button>
    </form>
    <p id="info_link"><a href="${request.route_path("chat_info", url=request.matchdict["url"])}">Edit chat info</a>\
% if from_homepage:
 · <a href="${request.route_path("home", url=request.matchdict["url"])}" id="search_again">Search again</a>\
% endif
</p>
  </section>
<%block name="scripts">
<script>cherubplay.chat("${request.matchdict["url"]}", "${request.context.chat_user.symbol_character}");</script>
</%block>
