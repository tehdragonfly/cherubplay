<%inherit file="base.mako" />\
  <h2>your chats</h2>
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
 unread" title="updated since your last visit\
% endif
">
      <h3><a href="${request.route_path("chat", url=chat.url)}">${chat_user.title or chat.url}</a>\
% if chat.updated>chat_user.visited:
 (unread)\
% endif
</h3>
% if prompt is not None:
      <p style="color: #${prompt.colour};">prompt: \
% if len(prompt.text)>250:
${prompt.text[:250]}...\
% else:
${prompt.text}\
% endif
</p>
% endif
% if chat_user.notes!="":
      <p>notes: ${chat_user.notes}</p>
% endif
      <form class="delete_form" action="${request.route_path("chat_delete", url=chat.url)}" method="post"><button type="submit">delete</button></form>
      <p><a href="${request.route_path("chat_notes", url=chat.url)}">edit title and notes</a></p>
    </li>
% endfor
  </ul>
% if paginator.page_count!=1:
  <p class="pager">
${paginator.pager(format='~5~')}
  </p>
% endif
% endif
<%block name="scripts"><script>cherubplay.chat_list();</script></%block>
