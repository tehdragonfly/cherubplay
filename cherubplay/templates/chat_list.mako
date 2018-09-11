<%inherit file="base.mako" />\
<%def name="render_title()">\
% if current_status is not None:
${current_status.capitalize()} chats\
% elif current_label is None:
Your chats\
% else:
Chats\
% endif
% if current_label is not None:
 labelled "${current_label.replace("_", " ")}"\
% endif
</%def>
<%block name="title">${render_title()} - </%block>
<%
    from cherubplay.lib import make_paginator
    paginator = make_paginator(request, chat_count, current_page)
%>
  <h2>${render_title()}</h2>
  <nav id="subnav">
    <section class="tile">
      <h3>Status</h3>
      <ul>
% if current_status is None and current_label is None:
        <li>All</li>
% else:
        <li><a href="${request.route_path("chat_list_label", label=current_label) if current_label else request.route_path("chat_list")}">All</a></li>
% endif
% if current_status == "unanswered":
        <li>Unanswered</li>
% else:
        <li><a href="${request.route_path("chat_list_status_label", status="unanswered", label=current_label) if current_label else request.route_path("chat_list_status", status="unanswered")}">Unanswered</a></li>
% endif
% if current_status == "ongoing":
        <li>Ongoing</li>
% else:
        <li><a href="${request.route_path("chat_list_status_label", status="ongoing", label=current_label) if current_label else request.route_path("chat_list_status", status="ongoing")}">Ongoing</a></li>
% endif
% if current_status == "ended":
        <li>Ended</li>
% else:
        <li><a href="${request.route_path("chat_list_status_label", status="ended", label=current_label) if current_label else request.route_path("chat_list_status", status="ended")}">Ended</a></li>
% endif
      </ul>
    </section>
% if labels:
    <section class="tile">
      <h3>Labels</h3>
      <ul>
  % if current_label is None:
        <li>All</li>
% else:
        <li><a href="${request.route_path("chat_list_status", status=current_status) if current_status else request.route_path("chat_list")}">All</a></li>
% endif
% for label, label_chat_count in labels:
% if current_label == label:
        <li>${label.replace("_", " ")} (${label_chat_count})</li>
% else:
        <li><a href="${request.route_path("chat_list_status_label", status=current_status, label=label) if current_status else request.route_path("chat_list_label", label=label)}">${label.replace("_", " ")} (${label_chat_count})</a></li>
% endif
% endfor
      </ul>
    </section>
% endif
  </nav>
% if len(chats)==0:
% if current_status is None:
  <p>You have no chats${" with this label" if current_label else ""}. <a href="${request.route_path("home")}">Search for a roleplaying partner to start chatting</a>.</p>
% else:
  <p>You have no ${current_status} chats${" with this label" if current_label else ""}. <a href="${request.route_path("chat_list")}">Check the full list</a> or <a href="${request.route_path("home")}">search for a roleplaying partner to start chatting</a>.</p>
% endif
% else:
  <section>
% if paginator.page_count!=1:
    <p class="pager tile">
${paginator.pager(format='~5~')|n}
    </p>
% endif
    <ul id="chat_list">
% for chat_user, chat, prompt in chats:
      <li class="tile\
% if chat.updated>chat_user.visited:
 unread" title="Updated since your last visit\
% endif
">
        <h3><a href="${request.route_path("chat", url=chat.url)}">${chat_user.display_title}</a>\
% if chat.updated>chat_user.visited:
 (unread)\
% elif current_status != "unanswered" and chat.last_user_id not in (None, request.user.id):
 (unanswered)\
% endif
</h3>
        <p class="subtitle">\
% if current_status is None:
${chat.status.capitalize()}. \
% endif
Started ${chat.created.strftime("%a %d %b %Y")}, last message ${chat.updated.strftime("%a %d %b %Y")}. <a href="${request.route_path("chat_info", url=chat.url)}">Edit chat info</a></p>
% if prompt is not None:
        <p style="color: #${prompt.colour};">Prompt: \
% if len(prompt.text)>250:
${prompt.formatter.as_plain_text()[:250]}...\
% else:
${prompt.formatter.as_plain_text()}\
% endif
</p>
% endif
% if chat_user.notes!="":
        <p class="notes">Notes: ${chat_user.notes}</p>
% endif
% if chat_user.labels:
        <p class="notes">Labels: \
% for label in chat_user.labels:
% if current_label == label:
${label.replace("_", " ")}${", " if not loop.last else ""}\
% else:
<a href="${request.route_path("chat_list_label", label=label)}">${label.replace("_", " ")}</a>${", " if not loop.last else ""}\
% endif
% endfor
</p>
% endif
      </li>
% endfor
    </ul>
% if paginator.page_count!=1:
    <p class="pager tile">
${paginator.pager(format='~5~')|n}
    </p>
% endif
  </section>
% endif
<%block name="scripts"></%block>
