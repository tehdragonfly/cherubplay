<%inherit file="/base.mako" />\
  <h2>ban</h2>
% if feedback:
  <p>${feedback}</p>
% endif
  <form action="${request.route_path("admin_ban")}" method="post">
    <p><label>username: <input type="text" name="username"></label><button type="submit">ditch the motherfucker</button></p>
  </form>
