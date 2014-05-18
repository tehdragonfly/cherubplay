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
      <p class="subtitle">Started ${chat.created.strftime("%a %d %b %Y")}, last message ${chat.updated.strftime("%a %d %b %Y")}. <a href="${request.route_path("chat_info", url=chat.url)}">Edit chat info</a></p>
% if prompt is not None:
      <p style="color: #${prompt.colour};">Prompt: \
% if len(prompt.text)>250:
${prompt.text[:250]}...\
% else:
${prompt.text}\
% endif
</p>
% endif
% if chat_user.notes!="":
      <p>Notes: ${chat_user.notes}</p>
% endif
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
