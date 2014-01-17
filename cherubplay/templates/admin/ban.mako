<%inherit file="/base.mako" />\
  <h2>Ban</h2>
% if feedback:
  <p>${feedback}</p>
% endif
  <form action="${request.route_path("admin_ban")}" method="post">
    <p><label>Username: <input type="text" name="username"></label><button type="submit">Ban</button></p>
  </form>
