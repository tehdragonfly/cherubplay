<%inherit file="base.mako" />\
<% from cherubplay.lib import timezones_list %>
<% from cherubplay.models.enums import MessageFormat %>
<%block name="title">Account settings - </%block>
  <h2>${request.user.username}</h2>
  <nav id="subnav">
    <section class="tile">
      <ul>
        <li>Settings</li>
        <li><a href="${request.route_path("account_connections")}">User connections</li>
        <li><a href="${request.route_path("account_export")}">Export your account data</li>
      </ul>
    </section>
    <form action="${request.route_path("account_layout_version")}" method="post">
      <section class="tile">
        <p>This is the old layout. <button type="submit">Try the new layout</button></p>
      </section>
      <input type="hidden" name="layout_version" value="2">
    </form>
  </nav>
% if request.GET.get("saved") == "verify_email":
  <p id="confirmation">We've sent you an e-mail. Please click the link in the e-mail to verify your address.</p>
% elif request.GET.get("saved") == "email_address":
  <p id="confirmation">Your e-mail address has been changed.</p>
% elif request.GET.get("saved") == "password":
  <p id="confirmation">Your password has been changed.</p>
% else:
  <p id="confirmation"></p>
% endif
  <div class="tile">
    <h3>E-mail address</h3>
    <form action="${request.route_path("account_email_address")}" method="post">
    <p>The e-mail address you provide here can be used to recover your account if you ever lose your password.</p>
% if email_address_error:
    <p>${email_address_error}</p>
% endif
    <p><label>E-mail address: <input type="email" name="email_address" maxlength="100" required value="${request.user.email or ""}"></label></p>
    <p><button type="submit">Save</button></p>
    </form>
% if request.user.email:
    <hr>
    <form action="${request.route_path("account_email_address_remove")}" method="post">
      <button type="submit">Remove email address</button>
    </form>
% endif
  </div>
  <form class="tile" action="${request.route_path("account_username")}" method="post">
    <h3>Username</h3>
% if username_error:
    <p>${username_error}</p>
% endif
    <p><label>Username: <input type="text" name="username" maxlength="100" required value="${request.user.username}"></label></p>
    <p><button type="submit">Save</button></p>
  </form>
  <form class="tile" action="${request.route_path("account_password")}" method="post">
    <h3>Password</h3>
% if password_error:
    <p>${password_error}</p>
% endif
    <p><label>Old password: <input type="password" name="old_password"></label></p>
    <p><label>New password: <input type="password" name="password"></label></p>
    <p><label>New password again: <input type="password" name="password_again"></label></p>
    <p><button type="submit">Save</button></p>
  </form>
  <form class="tile" action="${request.route_path("account_message_format")}" method="post">
    <h3>Message format</h3>
    <p>Plain text displays your messages exactly as you entered them. Markdown allows you to add simple formatting to your messages - examples include *asterisks* for <i>italic text</i>, **double asterisks** for bold text and # hashes for headings. <a href="https://daringfireball.net/projects/markdown/syntax#header" target="_blank" rel="noopener">See here</a> for a more comprehensive guide.</p>
    <% default_format = request.user.default_format or request.registry.settings["default_format"] %>
    <p><label><input type="radio" name="message_format" value="raw" ${"checked" if default_format == MessageFormat.raw else ""}> Save messages in plain text format</label></p>
    <p><label><input type="radio" name="message_format" value="markdown" ${"checked" if default_format == MessageFormat.markdown else ""}> Save messages in markdown format</label></p>
    <p class="actions"><div class="right"><button type="submit">Save</button></div></p>
  </form>
  <section class="tile">
    <h3>Chat options</h3>
    <p id="option_confirmation"></p>
    <p><label><input type="checkbox" id="sound_notifications"> Enable sound notifications</label></p>
    <p>If sound notifications aren't working for you, it may be because your browser doesn't allow autoplaying audio.</p>
    <p><label><input type="checkbox" id="enter_to_send"> Press enter to send</label></p>
  </section>
  <form class="tile" action="${request.route_path("account_timezone")}" method="post">
    <h3>Time zone</h3>
    <p class="middle_actions"><select name="timezone">
      % for timezone in timezones_list:
        <option value="${timezone}"\
% if timezone == request.user.timezone:
 selected="selected"\
% endif
>${timezone.replace("_", " ")}</option>
      % endfor
    </select><button type="submit">Save</button></p>
  </form>
  <form class="tile" action="${request.route_path("account_away_message")}" method="post">
    <h3>Away message</h3>
    <p>If you're leaving Cherubplay you can leave a message here to explain why. Your roleplaying partners will then see it when they visit chats with you.</p>
    <textarea class="full" name="away_message" maxlength="500" placeholder="Away message...">${request.user.away_message or ""}</textarea>
    <div class="actions">
      <div class="right"><button type="submit">Save</button></div>
    </div>
  </form>
<%block name="scripts"><script>cherubplay.account();</script></%block>
