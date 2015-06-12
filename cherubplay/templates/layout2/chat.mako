<%inherit file="../base.mako" />\
<%block name="title">${own_chat_user.title or chat.url} - </%block>
<%block name="body_class">layout2</%block>
<%def name="render_subnav(page, chat, own_chat_user)">\
  <div class="subnav">
    <nav>
      <h3>Navigation</h3>
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
  <div class="subnav"></div>
</%def>\
<%def name="render_message(message)">\
      <li id="message_${message.id}" class="message_${message.type}${" edited" if message.show_edited() else ""}" data-symbol="${symbols[message.symbol] if message.symbol is not None else ""}" style="color: #${message.colour};">
% if message.symbol is not None:
        <span class="symbol">${symbols[message.symbol]}</span>
% endif
% if message.symbol is not None and message.type=="system":
        <p>${message.text % symbols[message.symbol]}</p>
% else:
        <p>${message.text}</p>
% endif
        <div class="timestamp">${request.user.localise_time(message.posted).strftime("%Y-%m-%d %H:%M:%S")}${" · Edited" if message.show_edited() else ""}</div>
      </li>
</%def>\
<h2>${own_chat_user.title or chat.url}</h2>
<main>
${render_subnav("chat", chat, own_chat_user)}
  <div id="content">
    <ul id="messages">
% if prompt:
${render_message(prompt)}\
      <li class="message_system pager"><a href="${request.route_path("chat", url=request.matchdict["url"], _query={ "page": 1 })}">${message_count-26} more messages</a></li>
% endif
% for message in messages:
${render_message(message)}\
% endfor
    </ul>
  </div>
</main>
