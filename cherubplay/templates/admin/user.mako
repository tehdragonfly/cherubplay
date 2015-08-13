<%inherit file="../base.mako" />\
<%block name="title">#${user.id} ${user.username} - </%block>
  <h2>#${user.id} ${user.username}</h2>
% if request.GET.get("saved") == "status":
  <p>Status set to <strong>${user.status}</strong>.</p>
% endif
  <nav id="subnav">
    <section class="tile">
      <ul>
% if request.matched_route.name == "admin_user":
        <li>Main</li>
% else:
        <li><a href="${request.route_path("chat_list")}">Main</a></li>
% endif
      </ul>
    </section>
  </nav>
  <section class="tile">
    <h3>Info</h3>
    <p>Status: ${user.status.capitalize()}\
% if user.status == "banned" and user.unban_date is not None:
 (expires ${request.user.localise_time(user.unban_date).strftime("%d %b %Y, %H:%M:%S")})
% endif
</p>
    <p>E-mail address: ${user.email}</p>
    <p>Created: ${request.user.localise_time(user.created).strftime("%d %b %Y, %H:%M:%S")}\
% if request.user.timezone != user.timezone:
 (${user.localise_time(user.created).strftime("%d %b %Y, %H:%M:%S")})\
% endif
</p>
    <p>Last online: ${request.user.localise_time(user.last_online).strftime("%d %b %Y, %H:%M:%S")}\
% if request.user.timezone != user.timezone:
 (${user.localise_time(user.last_online).strftime("%d %b %Y, %H:%M:%S")})\
% endif
</p>
    <p>Time zone: ${user.timezone}</p>
    <p>Last IP address: ${user.last_ip}</p>
    <p>Layout version: ${user.layout_version}</p>
  </section>
  <section class="tile">
    <h3>Actions</h3>
    <form action="${request.route_path("admin_user_status", username=request.matchdict["username"])}" method="post">
      <p>Set status: <select name="status">
        <option value="active"\
% if user.status == "active":
 selected="selected"\
% endif
>Active</option>
        <option value="admin"\
% if user.status == "admin":
 selected="selected"\
% endif
>Admin</option>
        <option value="banned"\
% if user.status == "banned":
 selected="selected"\
% endif
>Banned</option>
      </select> <button type="submit">Save</button></p>
    </form>
% if user.status != "banned" and user.id != request.user.id:
    <form action="${request.route_path("admin_user_chat", username=request.matchdict["username"])}" method="post">
      <p><button type="submit">Chat with ${user.username}</button></p>
    </form>
    <form action="${request.route_path("admin_user_ban", username=request.matchdict["username"])}" method="post">
      <input type="hidden" name="days" value="1">
      <p><button type="submit">Ban for 1 day</button></p>
    </form>
    <form action="${request.route_path("admin_user_ban", username=request.matchdict["username"])}" method="post">
      <input type="hidden" name="days" value="7">
      <p><button type="submit">Ban for 7 days</button></p>
    </form>
% endif
  </section>
