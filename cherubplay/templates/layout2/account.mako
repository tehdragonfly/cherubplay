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
% if request.GET.get("saved")=="password":
    <p id="confirmation">Your password has been changed.</p>
% else:
    <p id="confirmation"></p>
% endif
    <form class="tile2" action="${request.route_path("account_password")}" method="post">
      <h3>Password</h3>
% if password_error:
      <p>${password_error}</p>
% endif
      <p><label>Old password: <input type="password" name="old_password"></label></p>
      <p><label>New password: <input type="password" name="password"></label></p>
      <p><label>New password again: <input type="password" name="password_again"></label></p>
      <p><button type="submit">Save</button></p>
    </form>
    <section class="tile2">
      <h3>Chat options</h3>
      <p><label><input type="checkbox" id="sound_notifications"> Enable sound notifications</label></p>
      <p><label><input type="checkbox" id="enter_to_send"> Press enter to send</label></p>
      <p><label><input type="checkbox" id="cross_chat_notifications"> Get notifications from other chats (desktop only)</label></p>
    </section>
  </div>
</main>
<%block name="scripts"><script>cherubplay.account();</script></%block>
