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
</%def>\
<%def name="render_chat(chat_user, chat, prompt=None, show_request=True)">\
      <li class="tile2\
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
Started ${request.user.localise_time(chat.created).strftime("%a %d %b %Y")}, last message ${request.user.localise_time(chat.updated).strftime("%a %d %b %Y")}. <a href="${request.route_path("chat_info", url=chat.url)}">Edit chat info</a></p>
        % if prompt is not None:
        % if len(prompt.text) <= 250:
        <p style="color: #${prompt.colour};">${prompt.text}</p>
        % else:
        <div class="expandable">
          <a class="toggle" href="${request.route_path("chat", url=chat.url, _query={"page": 1})}">(more)</a>
          <p class="expanded_content" style="color: #${prompt.colour};" data-href="${request.route_path("chat_ext", ext="json", url=chat.url, _query={"page": 1})}" data-type="chat"></p>
          <p class="collapsed_content" style="color: #${prompt.colour};">${prompt.text[:250]}...</p>
        </div>
        % endif
        % endif
        % if chat_user.notes != "" or chat_user.labels or (show_request and chat.request and (request.user.status == "admin" or chat.request.status == "posted" or chat.request.user_id == request.user.id)):
        <hr>
        % endif
        % if show_request and chat.request and (request.user.status == "admin" or chat.request.status in ("posted", "locked") or chat.request.user_id == request.user.id):
        <p class="notes">From request <a href="${request.route_path("directory_request", id=chat.request_id)}">#${chat.request_id}</a></p>
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
</%def>
<%block name="title">${render_title()} - </%block>
<%block name="body_class">layout2</%block>
<%
    from cherubplay.lib import make_paginator
    paginator = make_paginator(request, chat_count, current_page)
%>
<h2>${render_title()}</h2>

<main class="flex">
  <div class="side_column">
    <nav>
      <h3>Status</h3>
      <ul>
        % if current_status is None:
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
    </nav>
  </div>
  <div class="side_column">
    % if labels:
    <nav>
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
    </nav>
    % endif
  </div>
  <div id="content">
    % if len(chats)==0:
    % if current_status is None and current_label is None:
    <p>You have no chats${" with this label" if current_label else ""}. <a href="${request.route_path("home")}">Search for a roleplaying partner to start chatting</a>.</p>
    % else:
    <p>You have no ${current_status} chats${" with this label" if current_label else ""}. <a href="${request.route_path("chat_list")}">Check the full list</a> or <a href="${request.route_path("home")}">search for a roleplaying partner to start chatting</a>.</p>
    % endif
    % else:
    % if paginator.page_count!=1:
    <p class="pager tile2">
    ${paginator.pager(format='~5~')|n}
    </p>
    % endif
    <ul id="chat_list">
    % for chat_user, chat, prompt in chats:
    ${render_chat(chat_user, chat, prompt)}
    % endfor
    </ul>
    % if paginator.page_count!=1:
    <p class="pager tile2">
    ${paginator.pager(format='~5~')|n}
    </p>
    % endif
    % endif
  </div>
</main>
