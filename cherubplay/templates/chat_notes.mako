<%inherit file="base.mako" />\
  <h1>${chat.url}</h1>
% if request.environ["REQUEST_METHOD"]=="POST":
  <p>Your changes have been saved.</p>
% else:
  <p>Here, you can write notes on this chat to help you organise it. The information you post here is for your reference only and is not visible to anyone else.</p>
% endif
  <form class="tile" action="${request.route_path("chat_notes", url=request.matchdict["url"])}" method="post">
    <p><textarea id="notes" name="notes" placeholder="Notes..." rows="5">${own_chat_user.notes}</textarea></p>
    <button type="submit">Save</button>
  </form>
  <p><a href="${request.route_path("chat_list")}">Back to your chats</a></p>
