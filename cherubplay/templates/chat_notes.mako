<%inherit file="base.mako" />\
  <h1>${own_chat_user.title or chat.url}</h1>
% if request.environ["REQUEST_METHOD"]=="POST":
  <p>Your changes have been saved.</p>
% else:
  <p>Here, you can write a title and notes for this chat to help you organise it. The information you post here is for your reference only and is not visible to anyone else.</p>
% endif
  <form class="tile" action="${request.route_path("chat_notes", url=request.matchdict["url"])}" method="post">
    <h3><input type="text" id="chat_notes_title" name="title" placeholder="Title..." value="${own_chat_user.title}"></h3>
    <p><textarea id="chat_notes_notes" name="notes" placeholder="Notes..." rows="5">${own_chat_user.notes}</textarea></p>
    <button type="submit">Save</button>
  </form>
  <p><a href="${request.route_path("chat_list")}">Back to your chats</a></p>
