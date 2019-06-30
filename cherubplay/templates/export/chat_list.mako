<!DOCTYPE html>
<html>
<head>
<title>Your chats - Cherubplay</title>
<meta http-equiv="Content-Type" content="text/html;charset=utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta name="theme-color" content="#393">
<link rel="stylesheet" href="../cherubplay2.css">
</head>
<body class="layout2">

<header>
  <h1><img src="../logo.png" alt="Cherubplay"></h1>
</header>

<h2>Your chats</h2>

<main class="flex">
  <div id="content">
    <ul id="chat_list">
      % for chat, chat_user, prompt in chats:
      <li class="tile2\
% if chat.updated>chat_user.visited:
 unread" title="Updated since your last visit\
% endif
">
        <h3><a href="${chat.url}/1.html">${chat_user.display_title}</a>\
% if chat.updated>chat_user.visited:
 (unread)\
% elif current_status != "unanswered" and chat.last_user_id not in (None, user.id):
 (unanswered)\
% endif
</h3>
        <p class="subtitle">\
% if current_status is None:
${chat.status.capitalize()}. \
% endif
Started ${user.localise_time(chat.created).strftime("%a %d %b %Y")}, last message ${user.localise_time(chat.updated).strftime("%a %d %b %Y")}.</p>
        % if prompt is not None:
          <% was_trimmed, preview_text = prompt.text.trim_html(250) %>
          <div class="message" style="color: #${prompt.colour};">${preview_text}</div>
        % endif
        % if chat_user.notes != "" or chat_user.labels:
        <hr>
        % endif
        % if chat_user.notes != "":
        <p class="notes">Notes: ${chat_user.notes}</p>
        % endif
        % if chat_user.labels:
        <p class="notes">Labels: \
% for label in chat_user.labels:
${label.replace("_", " ")}${", " if not loop.last else ""}\
% endfor
</p>
      % endif
      </li>
      % endfor
    </ul>
  </div>
</main>

</body>
</html>