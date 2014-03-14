<%inherit file="/base.mako" />\
  <h2>chat</h2>
% if feedback:
  <p>${feedback}</p>
% endif
  <form action="${request.route_path("admin_chat")}" method="post">
    <p><label>username: <input type="text" name="username"></label><button type="submit">chat</button></p>
  </form>
