<%inherit file="base.mako" />\
<% from cherubplay.lib import timezones_list %>
<%block name="heading">Account settings</%block>
% if request.GET.get("saved") == "verify_email":
    <p id="confirmation">We've sent you an e-mail. Please click the link in the e-mail to verify your address.</p>
% elif request.GET.get("saved") == "email_address":
    <p id="confirmation">Your e-mail address has been changed.</p>
% elif request.GET.get("saved") == "password":
    <p id="confirmation">Your password has been changed.</p>
% endif
    <div class="tile2">
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
    <form class="tile2" action="${request.route_path("account_username")}" method="post">
      <h3>Username</h3>
% if username_error:
      <p>${username_error}</p>
% endif
      <p><label>Username: <input type="text" name="username" maxlength="100" required value="${request.user.username}"></label></p>
      <p><button type="submit">Save</button></p>
    </form>
    <form class="tile2" action="${request.route_path("account_password")}" method="post">
      <h3>Password</h3>
% if password_error:
      <p>${password_error}</p>
% endif
      <p><label>Old password: <input type="password" name="old_password" required></label></p>
      <p><label>New password: <input type="password" name="password" required></label></p>
      <p><label>New password again: <input type="password" name="password_again" required></label></p>
      <p><button type="submit">Save</button></p>
    </form>
    <section class="tile2">
      <h3>Chat options</h3>
      <p id="option_confirmation"></p>
      <p><label><input type="checkbox" id="sound_notifications"> Enable sound notifications</label></p>
      <p><label><input type="checkbox" id="enter_to_send"> Press enter to send</label></p>
      <p><label><input type="checkbox" id="cross_chat_notifications"> Get notifications from other chats (desktop only)</label></p>
    </section>
    <section class="tile2">
      <h3>Push notifications</h3>
      <noscript>Push notifications require JavaScript, so please enable JavaScript to receive them.</noscript>
      <div id="push_notifications_unsupported">
        <p>Sorry, your browser or device doesn't support push notifications.</p>
      </div>
      <div id="push_notifications_disabled">
        <p>Push notifications are currently disabled on this device.</p>
        <p id="push_notifications_denied">You've previously blocked push notifications on Cherubplay. You may need to remove the block in your browser's settings before you can enable push notifications.</p>
        <button id="enable_push_notifications">Enable push notifications</button>
      </div>
      <div id="push_notifications_enabled">
        <p>Push notifications are enabled on this device.</p>
        <button id="disable_push_notifications">Disable push notifications</button>
      </div>
    </section>
    % if request.user.status != "banned":
      <form class="tile2" action="${request.route_path("account_away_message")}" method="post">
        <h3>Away message</h3>
        <p>If you're leaving Cherubplay you can leave a message here to explain why. Your roleplaying partners will then see it when they visit chats with you.</p>
        <p>Note that if you have multiple chats with the same person then they'll be able to tell they're all you.</p>
        <textarea class="full" name="away_message" maxlength="500" placeholder="Away message...">${request.user.away_message or ""}</textarea>
        <div class="actions">
          <div class="right"><button type="submit">Save</button></div>
        </div>
      </form>
    % endif
    <form class="tile2" action="${request.route_path("account_timezone")}" method="post">
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
    <form class="tile2" action="${request.route_path("account_message_format")}" method="post">
      <h3>Message format</h3>
      <p><input type="radio" name="message_format" value="raw"> Save messages in plain text format</p>
      <p><input type="radio" name="message_format" value="markdown"> Save messages in markdown format</p>
      <p class="middle_actions"><button type="submit">Save</button></p>
    </form>
  </div>
<%block name="scripts"><script>cherubplay.account("${request.registry.settings.get("push.public_key", "")}");</script></%block>
