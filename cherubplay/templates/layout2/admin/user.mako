<%inherit file="../base.mako" />\
<%block name="title">#${request.context.id} ${request.context.username} - </%block>
<%block name="body_class">layout2</%block>
<h2>#${request.context.id} ${request.context.username}</h2>
<main class="flex">
  <div class="side_column">
    <nav>
      <ul>
% if request.matched_route.name == "admin_user":
        <li>Main</li>
% else:
        <li><a href="${request.route_path("chat_list")}">Main</a></li>
% endif
      </ul>
    </nav>
  </div>
  <div class="side_column"></div>
  <div id="content">
% if request.GET.get("saved") == "status":
    <p>Status set to <strong>${request.context.status}</strong>.</p>
% endif
    <section class="tile2">
      <h3>Info</h3>
      <p>Status: ${request.context.status.capitalize()}\
% if request.context.status == "banned" and request.context.unban_date is not None:
 (expires ${request.user.localise_time(request.context.unban_date).strftime("%d %b %Y, %H:%M:%S")})
% endif
</p>
      <p>E-mail address: ${request.context.email}</p>
      <p>Created: ${request.user.localise_time(request.context.created).strftime("%d %b %Y, %H:%M:%S")}\
% if request.user.timezone != request.context.timezone:
 (${request.context.localise_time(request.context.created).strftime("%d %b %Y, %H:%M:%S")})\
% endif
</p>
      <p>Last online: ${request.user.localise_time(request.context.last_online).strftime("%d %b %Y, %H:%M:%S")}\
% if request.user.timezone != request.context.timezone:
 (${request.context.localise_time(request.context.last_online).strftime("%d %b %Y, %H:%M:%S")})\
% endif
</p>
      <p>Time zone: ${request.context.timezone}</p>
      <p>Last IP address: ${request.context.last_ip}</p>
      <p>Layout version: ${request.context.layout_version}</p>
    </section>
    <section class="tile2">
      <h3>Actions</h3>
      <form action="${request.route_path("admin_user_status", username=request.matchdict["username"])}" method="post">
        <p>Set status: <select name="status">
          <option value="active"\
% if request.context.status == "active":
 selected="selected"\
% endif
>Active</option>
          <option value="admin"\
% if request.context.status == "admin":
 selected="selected"\
% endif
>Admin</option>
          <option value="banned"\
% if request.context.status == "banned":
 selected="selected"\
% endif
>Banned</option>
        </select> <button type="submit">Save</button></p>
      </form>
% if request.context.status != "banned" and request.context.id != request.user.id:
      <form action="${request.route_path("admin_user_ban", username=request.matchdict["username"])}" method="post">
        <input type="hidden" name="days" value="1">
        <p><button type="submit">Ban for 1 day</button></p>
      </form>
      <form action="${request.route_path("admin_user_ban", username=request.matchdict["username"])}" method="post">
        <input type="hidden" name="days" value="7">
        <p><button type="submit">Ban for 7 days</button></p>
      </form>
% endif
% if request.context.id != request.user.id:
      <form action="${request.route_path("admin_user_chat", username=request.matchdict["username"])}" method="post">
        <p><button type="submit">Chat with ${request.context.username}</button></p>
      </form>
% endif
      <form action="${request.route_path("admin_user_reset_password", username=request.matchdict["username"])}" method="post">
        <p><button type="submit">Reset password</button></p>
      </form>
    </section>
  </div>
</main>
