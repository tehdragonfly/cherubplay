<%inherit file="base.mako" />\
  <h2>Your chats</h2>
% if len(chats)==0:
  <p>You have no chats. <a href="${request.route_path("home")}">Search for a roleplaying partner to start chatting</a>.</p>
% else:
% if paginator.page_count!=1:
  <p class="pager">
${paginator.pager(format='~5~')}
  </p>
% endif
  <ul id="chat_list">
% for chat_user, chat, prompt in chats:
    <li class="tile\
% if chat.updated>chat_user.visited:
 unread" title="Updated since your last visit\
% endif
">
      <h3><a href="${request.route_path("chat", url=chat.url)}">${chat_user.title or chat.url}</a>\
% if chat.updated>chat_user.visited:
 (unread)\
% endif
</h3>
      <p style="color: #${prompt.colour};">Prompt: \
% if len(prompt.text)>250:
${prompt.text[:250]}...\
% else:
${prompt.text}\
% endif
</p>
% if chat_user.notes!="":
      <p>Notes: ${chat_user.notes}</p>
% endif
      <form class="delete_form" action="${request.route_path("chat_delete", url=chat.url)}" method="post"><button type="submit">Delete</button></form>
      <p><a href="${request.route_path("chat_notes", url=chat.url)}">Edit title/notes</a></p>
    </li>
% endfor
  </ul>
% if paginator.page_count!=1:
  <p class="pager">
${paginator.pager(format='~5~')}
  </p>
% endif
% endif
  <script src="http://code.jquery.com/jquery-2.0.3.min.js"></script>
  <script src="/static/chat_list.js?1"></script>
