<%inherit file="chat_base.mako" />\
<% from cherubplay.models.enums import ChatMode %>
<%block name="title">\
% if request.context.chat_user:
${"Archive - " if request.context.is_continuable else ""}${request.context.chat_user.display_title} - \
% endif
</%block>
<%
    from cherubplay.lib import make_paginator
    paginator = make_paginator(request, message_count, current_page)
%>
% if paginator.page_count > 1:
    <p class="pager tile2">
${paginator.pager(format='~5~')|n}
    </p>
% endif
% if messages:
    <ul id="messages" class="tile2">
% for message in messages:
${parent.render_message(message)}\
% endfor
% if paginator.page == paginator.page_count and request.context.chat_user and request.context.chat_user.draft:
      <li class="message_ooc">
        <p>${request.context.chat_user.draft}</p>
        <div class="timestamp">
          % if request.context.chat.mode == ChatMode.group and request.context.chat_user.handle:
            ${request.context.chat_user.handle} ·
          % endif
          Draft
        </div>
      </li>
% endif
% if paginator.page == paginator.page_count and request.context.is_continuable:
      <li class="message_system"><a href="${request.route_path("chat", url=request.matchdict["url"])}">Continue this chat</a></li>
% endif
    </ul>
% else:
    <p>No messages.</p>
% endif
% if paginator.page_count > 1:
    <p class="pager tile2">
${paginator.pager(format='~5~')|n}
    </p>
% endif
