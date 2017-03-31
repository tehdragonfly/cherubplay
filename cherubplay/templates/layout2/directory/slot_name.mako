<%inherit file="base.mako" />\
<%block name="heading">Request #${request.context.id}</%block>
<% from cherubplay.models import Tag %>
    % if error == "blank_name":
      <p>Please enter a name.</p>
    % endif
    <form action="${request.current_route_path()}" method="post" class="tile2">
      <p>Please enter a name to identify yourself in this chat.</p>
      <p><input type="text" name="name" class="full" maxlength="50" required placeholder="Your name..."></p>
      <div class="actions">
        <div class="right"><button type="submit">Answer</button></div>
      </div>
    </form>
