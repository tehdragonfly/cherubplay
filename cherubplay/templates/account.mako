<%inherit file="base.mako" />\
<%block name="title">Account settings - </%block>
  <h2>${request.user.username}</h2>
% if request.GET.get("saved")=="password":
  <p id="confirmation">Your password has been changed.</p>
% else:
  <p id="confirmation"></p>
% endif
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
    <h3>Notifications</h3>
    <p><label><input type="checkbox" id="sound_notifications"> Enable sound notifications</label></p>
  </section>
<%block name="scripts"><script>cherubplay.account();</script></%block>
