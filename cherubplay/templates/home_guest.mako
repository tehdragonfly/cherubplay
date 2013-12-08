<%inherit file="base.mako" />\
% if forbidden:
  <p>You need to logged in to access this page. Please sign up or log in below:</p>
% else:
  <p>BLAH BLAH BLAH WRITE SOME TEXT HERE</p>
% endif
  <h2>Create an account</h2>
% if sign_up_error:
  <p>${sign_up_error}</p>
% endif
  <form action="${request.route_path("sign_up")}" method="post" class="account_form">
    <input type="text" name="username" placeholder="Username..." maxlength="100">
    <input type="password" name="password" placeholder="Password...">
    <input type="password" name="password_again" placeholder="Password again...">
    <button type="submit">Sign up</button>
  </form>
  <h2>Log in</h2>
% if log_in_error:
  <p>${log_in_error}</p>
% endif
  <form action="${request.route_path("log_in")}" method="post" class="account_form">
    <input type="text" name="username" placeholder="Username..." maxlength="100">
    <input type="password" name="password" placeholder="Password...">
    <button type="submit">Log in</button>
  </form>
