<%inherit file="base.mako" />\
<%block name="body_class">layout2</%block>
<main>
  <h2>Forgotten your password?</h2>
  % if error == "limit":
  <div class="tile2">
    <p>Sorry, you can only reset your password once per day. Please wait until tomorrow.</p>
  </div>
  % elif saved:
  <div class="tile2">
    <p>We've sent you an e-mail with a link to reset your password.</p>
  </div>
  % else:
  <form action="${request.route_path("account_forgot_password")}" method="post" class="tile2">
    % if error == "no_user":
    <p>${forgot_password_error}</p>
    % elif error == "no_email":
    <p>This account doesn't have an e-mail address. Please <a href="https://cherubplay.tumblr.com/ask">send us an ask</a> instead.</p>
    % endif
    <p>Enter your username, and we'll e-mail you with a link to reset your password.</p>
    <p><input type="text" name="username" placeholder="Username..." maxlength="100"> <button type="submit">Send</button></p>
  </form>
  % endif
</main>
