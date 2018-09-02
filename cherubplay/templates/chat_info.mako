<%inherit file="base.mako" />\
<%namespace name="chat_base" file="chat.mako" />\
<%block name="title">Info - ${request.context.chat_user.display_title} - </%block>
${chat_base.render_subnav("info", request.context.chat, request.context.chat_user)}
% if request.GET.get("saved") == "end":
  <p>This chat has now been ended.</p>
% elif request.GET.get("saved") == "info":
  <p>Your changes have been saved.</p>
% else:
  <p>Here, you can write a title and notes for this chat to help you organise it. The information you post here is for your reference only and is not visible to anyone else.</p>
% endif
  <form class="tile" action="${request.route_path("chat_info", url=request.matchdict["url"])}" method="post">
    <h3><input type="text" id="chat_notes_title" name="title" placeholder="Title..." value="${request.context.chat_user.title}" maxlength="100"></h3>
    <p><textarea id="chat_notes_notes" name="notes" placeholder="Notes..." rows="5">${request.context.chat_user.notes}</textarea></p>
    <p><input type="text" id="chat_notes_labels" name="labels" placeholder="Labels..." value="${", ".join(_.replace("_", " ") for _ in request.context.chat_user.labels)}" maxlength="500"></textarea></p>
    <button type="submit">Save</button>
  </form>
% if request.context.chat.status == "ongoing" and len(request.context.active_chat_users) > 2:
  <section class="tile danger">
    <h3>Leave chat</h3>
    <p>If you leave this chat it will no longer appear on your chats page and you won't be able to take part in it, but the other participants will be able to continue.</p>
    <p>Leaving a chat is irreversible and cannot be undone, so please do not do this unless you're absolutely sure you're done with this chat.</p>
    <p class="links"><a href="${request.route_path("chat_leave", url=request.matchdict["url"])}">Leave chat</a></p>
  </section>
% elif request.context.chat.status == "ongoing":
  <section class="tile danger">
    <h3>End or delete chat</h3>
    <p>Ending a chat prevents any further messages from being sent, and deleting it also deletes it from the your chats page. These actions are both irreversible and cannot be undone, so please do not do them unless you're absolutely sure you're done with this chat.</p>
    <p class="links"><a href="${request.route_path("chat_end", url=request.matchdict["url"])}">End chat</a> · <a href="${request.route_path("chat_delete", url=request.matchdict["url"])}">Delete chat</a></p>
  </section>
% else:
  <section class="tile danger">
    <h3>Delete chat</h3>
    <p>Deleting a chat is irreversible and cannot be undone, so please do not do this unless you're absolutely sure you're done with this chat.</p>
    <p class="links"><a href="${request.route_path("chat_delete", url=request.matchdict["url"])}">Delete chat</a></p>
  </section>
% endif
  <p><a href="${request.route_path("chat_list")}">Back to your chats</a></p>
