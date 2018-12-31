<%inherit file="base.mako" />\
<%block name="body_class">layout2</%block>
<main>
% if forbidden:
  <h2>Access denied</h2>
  <p>You need to be logged in to access this page. Please sign up or log in below:</p>
% else:
  <h2>Welcome to ${"Sleuthplay" if sleuth else "Cherubplay"}</h2>
  <p>${"Sleuthplay" if sleuth else "Cherubplay"} is a paragraph-style roleplaying website for ${"Problem Sleuth" if sleuth else "Homestuck"} fans. Here, you can post your prompts, answer other people's prompts and chat with other roleplayers. To get started, sign up or log in below:</p>
% endif
  <section id="account_forms">
  <form action="${request.route_path("sign_up")}" method="post" class="tile2">
    <h3>Create an account</h3>
% if sign_up_error:
    <p>${sign_up_error}</p>
% endif
    <p><input type="text" name="username" placeholder="Username..." maxlength="100"></p>
    <p><input type="password" name="password" placeholder="Password..."></p>
    <p><input type="password" name="password_again" placeholder="Password again..."></p>
    <p><button type="submit">Sign up</button></p>
  </form>
  <form action="${request.route_path("log_in")}" method="post" class="tile2">
    <h3>Log in</h3>
% if log_in_error:
    <p>${log_in_error}</p>
% endif
    <p><input type="text" name="username" placeholder="Username..." maxlength="100"></p>
    <p><input type="password" name="password" placeholder="Password..."></p>
    <p><button type="submit">Log in</button></p>
    <p><a href="${request.route_path("account_forgot_password")}">Forgotten your password?</a></p>
  </form>
  </section>
</main>
