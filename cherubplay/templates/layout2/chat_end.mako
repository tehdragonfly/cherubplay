<%inherit file="chat_base.mako" />\
  <p>Are you sure you want to ${action} this chat?</p>
% if prompt:
  <section class="tile2">
    <h3>Prompt</h3>
    <div class="delete_preview message_${prompt.type}${" edited" if prompt.show_edited() else ""}" data-symbol="${symbols[prompt.symbol] if prompt.symbol is not None else ""}" style="color: #${prompt.colour};">
% if prompt.symbol is not None:
      <span class="symbol">${symbols[prompt.symbol]}</span>
% endif
% if prompt.symbol is not None and prompt.type=="system":
      <p>${prompt.text % symbols[prompt.symbol]}</p>
% else:
      <p>${prompt.text}</p>
% endif
      <div class="timestamp">${(request.user.localise_time(prompt.posted) if request.user is not None else prompt.posted).strftime("%Y-%m-%d %H:%M:%S")}</div>
    </div>
  </section>
% endif
% if last_message and last_message != prompt:
  <section class="tile2">
    <h3>Last message</h3>
    <div class="delete_preview message_${last_message.type}${" edited" if last_message.show_edited() else ""}" data-symbol="${symbols[last_message.symbol] if last_message.symbol is not None else ""}" style="color: #${last_message.colour};">
% if last_message.symbol is not None:
      <span class="symbol">${symbols[last_message.symbol]}</span>
% endif
% if last_message.symbol is not None and last_message.type=="system":
      <p>${last_message.text % symbols[last_message.symbol]}</p>
% else:
      <p>${last_message.text}</p>
% endif
      <div class="timestamp">${(request.user.localise_time(last_message.posted) if request.user is not None else last_message.posted).strftime("%Y-%m-%d %H:%M:%S")}</div>
    </div>
  </section>
% endif
  <form action="${request.route_path("chat_"+action, url=chat.url)}" method="post">
    <p><button type="submit">${action.capitalize()} chat</button></p>
  </form>
