<%inherit file="chat_base.mako" />\
<%block name="body_class">layout2 ongoing</%block>
    <ul id="messages" class="tile2">
% if prompt:
${parent.render_message(prompt)}\
      <li class="message_system"><a href="${request.route_path("chat", url=request.matchdict["url"], _query={ "page": 1 })}">${message_count-26} more messages</a></li>
% endif
% for message in messages:
${parent.render_message(message, show_edit=True)}\
% endfor
      <li id="status_bar">\
% if len(messages)>0:
Last message: ${request.user.localise_time(messages[-1].posted).strftime("%Y-%m-%d %H:%M:%S")}.\
% endif
</li>
      <li id="message_form_container">
        <form id="message_form" action="${request.route_path("chat_send", url=request.matchdict["url"])}" method="post">
          <p><input type="color" id="message_colour" name="message_colour" size="6" value="#${own_chat_user.last_colour}"> <select id="preset_colours" name="preset_colours">
% for hex, name in preset_colours:
            <option value="#${hex}">${name}</option>
% endfor
          </select><label title="Talk out of character; use ((double brackets)) to automatically OOC."><input id="message_ooc" type="checkbox" name="message_ooc"> OOC</label></p>
          <span class="symbol" style="color: #${own_chat_user.last_colour};">${symbols[own_chat_user.symbol]}</span>
          <p><textarea id="message_text" name="message_text" placeholder="Write a message..." style="color: #${own_chat_user.last_colour}">${own_chat_user.draft}</textarea></p>
          <button type="submit" id="send_button">Send</button>
        </form>
        <p id="info_link"><a href="${request.route_path("chat_info", url=request.matchdict["url"])}">Edit chat info</a>\
% if from_homepage:
 · <a href="${request.route_path("home", url=request.matchdict["url"])}" id="search_again">Search again</a>\
% endif
</p>
      </li>
    </ul>
<%block name="scripts">
<script>cherubplay.chat("${request.matchdict["url"]}", "${symbols[own_chat_user.symbol]}");</script>
</%block>
