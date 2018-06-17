<%inherit file="/layout2/base.mako" />\
<%block name="title">${next.heading()} - </%block>
<%block name="body_class">layout2</%block>
<h2><%block name="heading"></%block></h2>
<main class="flex">
  <div class="side_column">
    <nav>
      <ul>
        % if request.matched_route.name == "account":
          <li>Settings</li>
        % else:
          <li><a href="${request.route_path("account")}">Settings</a></li>
        % endif
        % if request.matched_route.name == "account_connections":
          <li>User connections</li>
        % else:
          <li><a href="${request.route_path("account_connections")}">User connections</a></li>
        % endif
      </ul>
      <form action="${request.route_path("account_layout_version")}" method="post">
        <input type="hidden" name="layout_version" value="1">
        <p>This is the new layout. <button type="submit">Return to the old layout</button></p>
      </form>
    </nav>
  </div>
  <div class="side_column"></div>
  <div id="content">
${next.body()}
  </div>
</main>
