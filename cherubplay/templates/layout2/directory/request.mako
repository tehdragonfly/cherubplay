<%inherit file="base.mako" />\
<%namespace name="chat_list" file="../chat_list.mako" />\
<%block name="heading">Request #${request.context.id}</%block>
    % if request.GET.get("answer_status") == "waiting":
    <p>You've answered this request. Once all the remaining slots are filled a new chat will be created.</p>
    % endif
    % if request.context.status == "draft" and request.context.duplicate_of_id:
    <p>This request has been taken down because it is a duplicate of <a href="${request.route_path("directory_request", id=request.context.duplicate_of_id)}">request #${request.context.duplicate_of_id}</a>.</p>
    % endif
    % if blacklisted_tags:
    % if request.context.status == "posted":
    <p>This request is visible to other users, but you can't see it in the directory because you've blacklisted some of its tags.</p>
    % elif request.context.status == "draft":
    <p>You've blacklisted some of this request's tags. When you post it, it'll be hidden from you but other users will be able to see it.</p>
    % endif
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
