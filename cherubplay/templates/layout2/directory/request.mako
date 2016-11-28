<%inherit file="base.mako" />\
<%namespace name="chat_list" file="../chat_list.mako" />\
<%block name="heading">Request #${request.context.id}</%block>
    % if blacklisted_tags:
    <p>This request is public, but you can't see it in the directory because you've blacklisted some of its tags.</p>
    % endif
    % if "too_many_requests" in request.GET:
    <p>You can't post more than 10 requests at a time. Please save another request as a draft before posting this one.</p>
    % endif
    <section class="tile2 request ${request.context.status}">
      ${parent.render_request(request.context, expanded=True)}
    </section>
    % if chats:
    <ul id="chat_list">
    % for chat_user, chat in chats:
    ${chat_list.render_chat(chat_user, chat, show_request=False)}
    % endfor
    </ul>
    % endif
