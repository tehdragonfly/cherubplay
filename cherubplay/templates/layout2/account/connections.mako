<%inherit file="base.mako" />\
<%block name="heading">User connections</%block>
    <section class="tile2">
      <ul class="tag_list">
        <li>
          <form id="account_connections_new" action="${request.route_path("account_connections_new")}" method="post">
            <input type="text" name="to" placeholder="Username..." maxlength="100">
            <button type="submit">Add</button>
          </form>
          % if error == "to_invalid":
            <span class="error">Sorry, that's not a valid username.</span>
          % endif
        </li>
        % for connection in connections:
          <li>${connection.to_username}</li>
        % endfor
      </ul>
    </section>