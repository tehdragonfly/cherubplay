<%inherit file="base.mako" />\
<%namespace name="chat" file="chat.mako" />\
% if symbol_users:
  <section class="tile">
    <h3>Users</h3>
    <ul>
% for symbol, user in symbol_users.items():
      <li>${symbols[symbol]} is #${user.id} <strong>${user.username}</strong> (${user.status}).</li>
% endfor
    </ul>
  </section>
% endif
% if paginator.page_count!=1:
  <p class="pager tile">
${paginator.pager(format='~5~')}
  </p>
% endif
  <ul id="messages">
% for message in messages:
${chat.render_message(message)}\
% endfor
  </ul>
% if paginator.page == paginator.page_count and continuable:
  <p class="continue tile"><a href="${request.route_path("chat", url=request.matchdict["url"])}">Continue this chat</a></p>
% endif
% if paginator.page_count != 1:
  <p class="pager tile">
${paginator.pager(format='~5~')}
  </p>
% endif
