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
          <li>
            <div class="actions">
              <div class="left">${connection.to_username}</div>
              <div class="right">
                <form action="${request.route_path("account_connection_delete", username=connection.to_username)}" method="post">
                  <button type="submit">Delete</button>
                </form>
                ·
                % if connection.is_mutual:
                  <form action="${request.route_path("account_connection_chat", username=connection.to_username)}" method="post">
                    <button type="submit">Chat</button>
                  </form>
                % else:
                  <button disabled title="You can't chat with this person until they accept the connection.">Chat</button>
                % endif
              </div>
            </div>
          </li>
        % endfor
      </ul>
    </section>