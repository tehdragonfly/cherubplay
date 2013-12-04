<%inherit file="base.mako" />\
  <h2>Your chats</h2>
  <ul id="chat_list">
% for chat_user, chat, prompt in chats:
    <li class="tile\
% if chat.updated>chat_user.visited:
 unread" title="Updated since your last visit\
% endif
">
      <h3><a href="${request.route_path("chat", url=chat.url)}">${chat.url}</a></h3>
      <p style="color: #${prompt.colour};">Prompt: \
% if len(prompt.text)>150:
${prompt.text[:150]}...\
% else:
${prompt.text}\
% endif
</p>
    </li>
% endfor
  </ul>
