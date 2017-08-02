<%inherit file="base.mako" />\
<%block name="title">Account settings - </%block>
  <h2>${request.user.username}</h2>
  <nav id="subnav">
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
  <form class="tile" action="${request.route_path("account_email_address")}" method="post">
    <h3>E-mail address</h3>
% if email_address_error:
    <p>${email_address_error}</p>
% endif
    <p><label>E-mail address: <input type="email" name="email_address" maxlength="100" required value="${request.user.email or ""}"></label></p>
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
  <section class="tile">
    <h3>Chat options</h3>
    <p id="option_confirmation"></p>
    <p><label><input type="checkbox" id="sound_notifications"> Enable sound notifications</label></p>
    <p><label><input type="checkbox" id="enter_to_send"> Press enter to send</label></p>
  </section>
<%block name="scripts"><script>cherubplay.account();</script></%block>
