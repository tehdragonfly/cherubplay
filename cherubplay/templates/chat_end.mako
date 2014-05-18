<%inherit file="base.mako" />\
  <h1>${own_chat_user.title or chat.url}</h1>
  <p>Are you sure you want to ${action} this chat?</p>
% if prompt:
  <section class="tile message_${prompt.type}">
    <h3>Prompt</h3>
% if prompt.symbol is not None:
% if prompt.type=="system":
      <p style="color: #${prompt.colour};">${prompt.text % symbols[prompt.symbol]}</p>
% else:
      <p style="color: #${prompt.colour};">${symbols[prompt.symbol]}: ${prompt.text}</p>
% endif
% else:
      <p style="color: #${prompt.colour};">${prompt.text}</p>
% endif
  </section>
% endif
% if last_message and last_message != prompt:
  <section class="tile message_${last_message.type}">
    <h3>Last message</h3>
% if last_message.symbol is not None:
% if last_message.type=="system":
      <p style="color: #${last_message.colour};">${last_message.text % symbols[last_message.symbol]}</p>
% else:
      <p style="color: #${last_message.colour};">${symbols[last_message.symbol]}: ${last_message.text}</p>
% endif
% else:
      <p style="color: #${last_message.colour};">${last_message.text}</p>
% endif
  </section>
% endif
  <form action="${request.route_path("chat_"+action, url=chat.url)}" method="post">
    <p><button type="submit">${action.capitalize()} chat</button></p>
  </form>
