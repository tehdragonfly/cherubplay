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
      % if banned:
      <li class="message_system">This user has been ${banned} banned from Cherubplay.</li>
      % endif
    </ul>
    <div id="status_bar" class="tile2 pager">&nbsp;</div>
    <section id="message_form_container" class="tile2">
      <form id="message_form" action="${request.route_path("chat_send", url=request.matchdict["url"])}" method="post">
        <div class="actions">
          <div class="left"><input type="color" id="message_colour" name="message_colour" size="6" value="#${own_chat_user.last_colour}"> <select id="preset_colours" name="preset_colours">
            % for hex, name in preset_colours:
            <option value="#${hex}">${name}</option>
            % endfor
          </select></div>
          <label class="right" title="Talk out of character; use ((double brackets)) to automatically OOC."><input id="message_ooc" type="checkbox" name="message_ooc"> OOC</label>
        </div>
        <span class="symbol" style="color: #${own_chat_user.last_colour};">${own_chat_user.symbol_character}</span>
        <p><textarea id="message_text" name="message_text" placeholder="Write a message..." style="color: #${own_chat_user.last_colour}">${own_chat_user.draft}</textarea></p>
        <div class="actions">
          <div class="right"><button type="submit" id="send_button">Send</button></div>
          <div id="info_link" class="left"><a href="${request.route_path("chat_info", url=request.matchdict["url"])}">Edit chat info</a>\
% if from_homepage:
 · <a href="${request.route_path("home", url=request.matchdict["url"])}" id="search_again">Search again</a>\
% endif
</div>
        </div>
      </form>
    </section>
    <section id="notification" class="tile2">
        <h3><a id="notification_title" target="_blank"></a></h3>
        <div id="notification_inner">
          <span id="notification_symbol" class="symbol"></span>
          <p id="notification_text"></p>
        </div>
        <button id="notification_close">Close</button>
    </section>
<%block name="scripts">
<script>cherubplay.chat("${request.matchdict["url"]}", "${own_chat_user.symbol_character}");</script>
</%block>
