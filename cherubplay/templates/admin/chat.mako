<%inherit file="/base.mako" />\
  <h2>Chat</h2>
% if feedback:
  <p>${feedback}</p>
% endif
  <form action="${request.route_path("admin_chat")}" method="post">
    <p><label>Username: <input type="text" name="username"></label><button type="submit">Chat</button></p>
  </form>
