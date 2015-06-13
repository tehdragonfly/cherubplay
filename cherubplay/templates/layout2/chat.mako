<%inherit file="base.mako" />\
<%block name="title">${own_chat_user.title or chat.url} - </%block>
<%block name="body_class">layout2 ongoing</%block>
<%def name="render_subnav(page, chat, own_chat_user)">\
  <div class="subnav">
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
    <ul id="messages" class="tile2">
% if prompt:
${render_message(prompt)}\
      <li class="message_system pager"><a href="${request.route_path("chat", url=request.matchdict["url"], _query={ "page": 1 })}">${message_count-26} more messages</a></li>
% endif
% for message in messages:
${render_message(message)}\
% endfor
      <li id="status_bar">\
% if len(messages)>0:
Last message: ${request.user.localise_time(messages[-1].posted).strftime("%Y-%m-%d %H:%M:%S")}.\
% endif
</li>
      <li id="message_form_container">
        <form id="message_form" action="${request.route_path("chat_send", url=request.matchdict["url"])}" method="post">
          <p><input type="color" id="message_colour" name="message_colour" size="6" value="#${own_chat_user.last_colour}"> <select id="preset_colours" name="preset_colours">
% for hex, name in preset_colours:
            <option value="#${hex}">${name}</option>
% endfor
          </select><label title="Talk out of character; use ((double brackets)) to automatically OOC."><input id="message_ooc" type="checkbox" name="message_ooc"> OOC</label></p>
          <span class="symbol">${symbols[own_chat_user.symbol]}</span>
          <p><textarea id="message_text" name="message_text" placeholder="Write a message..." style="color: #${own_chat_user.last_colour}">${own_chat_user.draft}</textarea></p>
          <button type="submit" id="send_button">Send</button>
        </form>
        <p id="info_link"><a href="${request.route_path("chat_info", url=request.matchdict["url"])}">Edit chat info</a>\
% if from_homepage:
 · <a href="${request.route_path("home", url=request.matchdict["url"])}" id="search_again">Search again</a>\
% endif
</p>
      </li>
    </ul>
  </div>
</main>
