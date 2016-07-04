<%inherit file="base.mako" />\
<%block name="body_class">layout2</%block>
<main>
  <h2>Reset your password</h2>
  <form action="${request.route_path("account_reset_password", _query=request.GET)}" method="post" class="tile2">
    <p>Choose your new password.</p>
    % if error == "no_password":
    <p>Please don't use a blank password.</p>
    % endif
    <p><input type="password" name="password" placeholder="Password..."> <button type="submit">Save</button></p>
  </form>
</main>
