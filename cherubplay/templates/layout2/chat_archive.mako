<%inherit file="chat_base.mako" />\
<%block name="title">\
% if own_chat_user:
${"Archive - " if continuable else ""}${own_chat_user.title or chat.url} - \
% endif
</%block>
% if paginator.page_count > 1:
    <div class="pager tile2">
${paginator.pager(format='~5~')}
    </div>
% endif
% if messages:
    <ul id="messages" class="tile2">
% for message in messages:
${parent.render_message(message)}\
% endfor
% if paginator.page == paginator.page_count and continuable:
      <li class="message_system"><a href="${request.route_path("chat", url=request.matchdict["url"])}">Continue this chat</a></li>
% endif
    </ul>
% else:
    <p>No messages.</p>
% endif
% if paginator.page_count > 1:
    <div class="pager tile2">
${paginator.pager(format='~5~')}
    </div>
% endif
