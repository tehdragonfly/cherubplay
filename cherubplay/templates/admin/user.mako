<%inherit file="../base.mako" />\
  <h2>#${user.id} ${user.username}</h2>
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
    <p>Status: ${user.status}</p>
    <p>E-mail address: ${user.email}</p>
    <p>Created: ${user.created}</p>
    <p>Last online: ${user.last_online}</p>
    <p>Last IP address: ${user.last_ip}</p>
  </section>
