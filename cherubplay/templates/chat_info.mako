<%inherit file="base.mako" />\
  <h1>${own_chat_user.title or chat.url}</h1>
% if request.GET.get("saved") == "end":
  <p>This chat has now been ended.</p>
% elif request.GET.get("saved") == "info":
  <p>Your changes have been saved.</p>
% else:
  <p>Here, you can write a title and notes for this chat to help you organise it. The information you post here is for your reference only and is not visible to anyone else.</p>
% endif
  <form class="tile" action="${request.route_path("chat_info", url=request.matchdict["url"])}" method="post">
    <h3><input type="text" id="chat_notes_title" name="title" placeholder="Title..." value="${own_chat_user.title}"></h3>
    <p><textarea id="chat_notes_notes" name="notes" placeholder="Notes..." rows="5">${own_chat_user.notes}</textarea></p>
    <button type="submit">Save</button>
  </form>
% if chat.status == "ongoing":
  <section class="tile danger">
    <h3>End or delete chat</h3>
    <p>Ending a chat prevents any further messages from being sent, and deleting it also deletes it from the your chats page. These actions are both irreversible and cannot be undone, so please do not do them unless you're absolutely sure you're done with this chat.</p>
    <p class="links"><a href="${request.route_path("chat_end", url=request.matchdict["url"])}">End chat</a> · <a href="${request.route_path("chat_delete", url=request.matchdict["url"])}">Delete chat</a></p>
  </section>
% else:
  <section class="tile danger">
    <h3>Delete chat</h3>
    <p>Deleting a chat is irreversible and cannot be undone, so please do not do them unless you're absolutely sure you're done with this chat.</p>
    <p class="links"><a href="${request.route_path("chat_delete", url=request.matchdict["url"])}">Delete chat</a></p>
  </section>
% endif
  <p><a href="${request.route_path("chat_list")}">Back to your chats</a></p>
