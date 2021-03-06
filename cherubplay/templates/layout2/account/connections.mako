<%inherit file="base.mako" />\
<%block name="heading">User connections</%block>
    <p>User connections allow you to chat with specific Cherubplay users.</p>
    <p>Enter the username of someone you'd like to connect to, and when they do the same with your username you'll be able to begin a chat.</p>
    <section class="tile2">
      <ul class="tag_list">
        % if "shutdown.user_connections" not in request.registry.settings:
        <li>
          <form id="account_connections_new" action="${request.route_path("account_connections_new")}" method="post">
            <input type="text" name="to" placeholder="Username..." maxlength="100">
            <button type="submit">Add</button>
          </form>
          % if error == "to_invalid":
            <span class="error">Sorry, that's not a valid username.</span>
          % elif error == "to_self":
            <span class="error">Sorry, you can't add yourself.</span>
          % endif
        </li>
        % endif
        % if connections:
        % for connection in connections:
          <li>
            <div class="actions">
              <div class="left">
                % if connection.is_mutual:
                  <a href="${request.route_path("chat_list_label", label=connection.to_username)}">${connection.to_username}</a>
                % elif not connection.is_mutual:
                  ${connection.to_username} (pending)
                % endif
              </div>
              % if "shutdown.user_connections" not in request.registry.settings:
              <div class="right">
                <a href="${request.route_path("account_connection_delete", username=connection.to_username)}">Delete</a>
                ·
                % if connection.is_mutual:
                  <form action="${request.route_path("account_connection_chat", username=connection.to_username)}" method="post">
                    <button type="submit">Chat</button>
                  </form>
                % else:
                  <button disabled title="You can't chat with this person until they accept the connection.">Chat</button>
                % endif
              </div>
              % endif
            </div>
          </li>
        % endfor
        % else:
          <li>You have no connections.</li>
        % endif
      </ul>
    </section>