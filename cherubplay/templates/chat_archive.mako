<%inherit file="base.mako" />\
<%namespace name="chat_base" file="chat.mako" />\
<%block name="title">\
% if request.context.chat_user:
${"Archive - " if request.context.is_continuable else ""}${request.context.chat_user.display_title} - \
% endif
</%block>
<%
    from cherubplay.lib import make_paginator
    paginator = make_paginator(request, message_count, current_page)
%>
% if request.context.chat_user:
${chat_base.render_subnav("archive", request.context.chat, request.context.chat_user)}
% endif
% if symbol_users:
${chat_base.user_list(symbol_users)}
% endif
% if paginator.page_count > 1:
  <p class="pager tile">
${paginator.pager(format='~5~')|n}
  </p>
% endif
% if messages:
  <ul id="messages">
% for message in messages:
${chat_base.render_message(message)}\
% endfor
  </ul>
% else:
  <p>No messages.</p>
% endif
% if paginator.page == paginator.page_count and request.context.is_continuable:
  <p class="continue tile"><a href="${request.route_path("chat", url=request.matchdict["url"])}">Continue this chat</a></p>
% endif
% if paginator.page_count > 1:
  <p class="pager tile">
${paginator.pager(format='~5~')|n}
  </p>
% endif
