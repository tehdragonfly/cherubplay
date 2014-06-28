<%inherit file="base.mako" />\
  <h2>Your chats</h2>
% if len(chats)==0:
  <p>You have no chats. <a href="${request.route_path("home")}">Search for a roleplaying partner to start chatting</a>.</p>
% else:
  <nav id="subnav">
    <section class="tile">
      <h3>Status</h3>
      <ul>
% if request.matched_route.name == "chat_list":
        <li>All</li>
% else:
        <li><a href="${request.route_path("chat_list")}">All</a></li>
% endif
% if request.matched_route.name == "chat_list_ongoing":
        <li>Ongoing</li>
% else:
        <li><a href="${request.route_path("chat_list_ongoing")}">Ongoing</a></li>
% endif
% if request.matched_route.name == "chat_list_ended":
        <li>Ended</li>
% else:
        <li><a href="${request.route_path("chat_list_ended")}">Ended</a></li>
% endif
      </ul>
    </section>
  </nav>
  <section>
% if paginator.page_count!=1:
    <p class="pager tile">
${paginator.pager(format='~5~')}
    </p>
% endif
    <ul id="chat_list">
% for chat_user, chat, prompt, last_message in chats:
      <li class="tile\
% if chat.updated>chat_user.visited:
 unread" title="Updated since your last visit\
% endif
">
        <h3><a href="${request.route_path("chat", url=chat.url)}">${chat_user.title or chat.url}</a>\
% if chat.updated>chat_user.visited:
 (unread)\
% elif last_message is not None and last_message.user_id not in (None, request.user.id):
 (unanswered)\
% endif
</h3>
        <p class="subtitle">\
% if request.matched_route.name == "chat_list":
${chat.status.capitalize()}. \
% endif
Started ${chat.created.strftime("%a %d %b %Y")}, last message ${chat.updated.strftime("%a %d %b %Y")}. <a href="${request.route_path("chat_info", url=chat.url)}">Edit chat info</a></p>
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
    <p class="pager tile">
${paginator.pager(format='~5~')}
    </p>
% endif
  </section>
% endif
<%block name="scripts"></%block>
