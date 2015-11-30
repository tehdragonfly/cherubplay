<%inherit file="base.mako" />\
<%namespace name="chat_list" file="../chat_list.mako" />\
<%block name="heading">Request #${request.context.id}</%block>
    <section class="tile2 request">
      ${parent.render_request(request.context, expanded=True)}
    </section>
    % if chats:
    <ul id="chat_list">
    % for chat_user, chat in chats:
    ${chat_list.render_chat(chat_user, chat)}
    % endfor
    </ul>
    % endif
