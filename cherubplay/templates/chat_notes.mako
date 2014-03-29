<%inherit file="base.mako" />\
  <h1>${own_chat_user.title or chat.url}</h1>
% if request.environ["REQUEST_METHOD"]=="POST":
  <p>Your changes have been saved.</p>
% else:
  <p>here you can write some stuff about this chat</p>
  <p>its like mumbling to yourself</p>
  <p>except here other people actually cant hear you</p>
  <p>rather than just pretending they cant to protect your self esteem</p>
% endif
  <form class="tile" action="${request.route_path("chat_notes", url=request.matchdict["url"])}" method="post">
    <h3><input type="text" id="chat_notes_title" name="title" placeholder="title" value="${own_chat_user.title}"></h3>
    <p><textarea id="chat_notes_notes" name="notes" placeholder="notes" rows="5">${own_chat_user.notes}</textarea></p>
    <button type="submit">save</button>
  </form>
  <p><a href="${request.route_path("chat_list")}">back to your chats</a></p>
