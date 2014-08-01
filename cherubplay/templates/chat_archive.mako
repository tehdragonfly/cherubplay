<%inherit file="base.mako" />\
<%namespace name="chat" file="chat.mako" />\
% if symbol_users:
${chat.user_list(symbol_users)}
% endif
% if paginator.page_count > 1:
  <p class="pager tile">
${paginator.pager(format='~5~')}
  </p>
% endif
% if messages:
  <ul id="messages">
% for message in messages:
${chat.render_message(message)}\
% endfor
  </ul>
% else:
  <p>No messages.</p>
% endif
% if paginator.page == paginator.page_count and continuable:
  <p class="continue tile"><a href="${request.route_path("chat", url=request.matchdict["url"])}">Continue this chat</a></p>
% endif
% if paginator.page_count > 1:
  <p class="pager tile">
${paginator.pager(format='~5~')}
  </p>
% endif