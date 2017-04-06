<%inherit file="base.mako" />\
<%block name="title">Account settings - </%block>
<%block name="body_class">layout2</%block>
<h2>${request.user.username}</h2>
<main class="flex">
  <div class="side_column"></div>
  <div class="side_column">
    <nav>
      <form action="${request.route_path("account_layout_version")}" method="post">
        <input type="hidden" name="layout_version" value="1">
        <p>This is the new layout. <button type="submit">Return to the old layout</button></p>
      </form>
    </nav>
  </div>
  <div id="content">
% if request.GET.get("saved") == "verify_email":
    <p id="confirmation">We've sent you an e-mail. Please click the link in the e-mail to verify your address.</p>
% elif request.GET.get("saved") == "email_address":
    <p id="confirmation">Your e-mail address has been changed.</p>
% elif request.GET.get("saved") == "password":
    <p id="confirmation">Your password has been changed.</p>
% else:
    <p id="confirmation"></p>
% endif
    <form class="tile2" action="${request.route_path("account_email_address")}" method="post">
      <h3>E-mail address</h3>
% if email_address_error:
      <p>${email_address_error}</p>
% endif
      <p><label>E-mail address: <input type="email" name="email_address" maxlength="100" required value="${request.user.email or ""}"></label></p>
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
  </div>
</main>
<%block name="scripts"><script>cherubplay.account();</script></%block>
