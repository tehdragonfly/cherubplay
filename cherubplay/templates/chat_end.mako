<%inherit file="base.mako" />\
<% from cherubplay.models.enums import MessageType %>\
<%namespace name="chat_base" file="chat.mako" />\
<%block name="title">${own_chat_user.title or chat.url} - </%block>
${chat_base.render_subnav(action, chat, own_chat_user)}
  <p>Are you sure you want to ${action} this chat?</p>
% if prompt:
  <section class="tile message_${prompt.type.value}">
    <h3>Prompt</h3>
% if prompt.symbol is not None:
% if prompt.type == MessageType.system:
      <p style="color: #${prompt.colour};">${prompt.text % prompt.symbol_character}</p>
% else:
      <p style="color: #${prompt.colour};">${prompt.symbol_character}: ${prompt.text}</p>
% endif
% else:
      <p style="color: #${prompt.colour};">${prompt.text}</p>
% endif
  </section>
% endif
% if last_message and last_message != prompt:
  <section class="tile message_${last_message.type.value}">
    <h3>Last message</h3>
% if last_message.symbol is not None:
% if last_message.type == MessageType.system:
      <p style="color: #${last_message.colour};">${last_message.text % last_message.symbol_character}</p>
% else:
      <p style="color: #${last_message.colour};">${last_message.symbol_character}: ${last_message.text}</p>
% endif
% else:
      <p style="color: #${last_message.colour};">${last_message.text}</p>
% endif
  </section>
% endif
  <form action="${request.route_path("chat_"+action, url=chat.url)}" method="post">
    <p><button type="submit">${action.capitalize()} chat</button></p>
  </form>
