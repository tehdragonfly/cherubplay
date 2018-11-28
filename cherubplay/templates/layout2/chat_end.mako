<%inherit file="chat_base.mako" />\
<% from cherubplay.models.enums import MessageType %>\
  <p>Are you sure you want to ${action} this chat?</p>
% if prompt:
  <section class="tile2">
    <h3>Prompt</h3>
    <div class="delete_preview message_${prompt.type.value}${" edited" if prompt.show_edited else ""}" data-symbol="${prompt.symbol_character if prompt.symbol is not None else ""}" style="color: #${prompt.colour};">
      ${parent.render_message_inner(request.context.chat, request.user, request.context.chat_user, prompt, False)}
    </div>
  </section>
% endif
% if last_message and last_message != prompt:
  <section class="tile2">
    <h3>Last message</h3>
    <div class="delete_preview message_${last_message.type.value}${" edited" if last_message.show_edited else ""}" data-symbol="${last_message.symbol_character if last_message.symbol is not None else ""}" style="color: #${last_message.colour};">
      ${parent.render_message_inner(request.context.chat, request.user, request.context.chat_user, last_message, False)}
    </div>
  </section>
% endif
  <form class="actions" action="${request.route_path("chat_"+action, url=request.context.chat.url)}" method="post">
    <div class="right"><button type="submit">${action.capitalize()} chat</button></div>
  </form>
