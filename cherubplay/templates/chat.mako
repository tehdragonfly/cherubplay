<%inherit file="base.mako" />\
  <ul id="messages">
% for message, chat_user in messages:
    <li class="tile message_${message.type}">
      <p style="color: #${message.colour};">\
% if chat_user is not None:
${chat_user.counter}: \
% endif
${message.text}</p>
    </li>
% endfor
  </ul>
% if continuable:
  <section id="status_bar">Last message: ${messages[-1][0].posted}.</section>
  <section id="message_form_container" class="tile">
    <form id="message_form">
      <p>
        <input type="color" id="prompt_colour" size="6" value="#000000">
        <select id="prompt_colour_presets">
          <option value="#000000">Basic black</option>
          <option value="#FFFFFF">Mysterious white</option>
        </select>
      </p>
      <p><textarea id="prompt_textarea" placeholder="Write a message..."></textarea></p>
      <button type="button" id="send_button">Send</button>
    </form>
    <form id="end_form"><button type="button">End chat</button></form>
  </section>
% endif
