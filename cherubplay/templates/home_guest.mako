<%inherit file="base.mako" />\
% if "cherubplay.read_only" in request.registry.settings:
  <p>CHERUBPLAY is a paragraph-style roleplaying website for Homestuck fans. Here, you can post your prompts, answer other people's prompts and chat with other roleplayers.</p>
  <p>The site is currently in read-only mode, so it isn't possible to sign up or log in right now. Please check <a href="http://cherubplay.tumblr.com/">the CHERUBPLAY blog</a> for updates.</p>
% else:
% if forbidden:
  <p>sorry only masters of the sweetest ironies are allowed to see this page</p>
  <p>register or log in below</p>
% else:
  <p>welcome to striderplay where all the striders hang out</p>
  <p>a million striders from a million timelines</p>
  <p>all gathered together to share the illest prompts and have the sweetest roleplays</p>
  <p>its like one big strider family orgy</p>
  <p>but without the sex because that would be weird</p>
  <p>if you have what it takes to get the wicked shit up in this place then sign up or log in below</p>
% endif
  <h2>join the family</h2>
% if sign_up_error:
  <p>${sign_up_error}</p>
% endif
  <form action="${request.route_path("sign_up")}" method="post" class="account_form">
    <input type="text" name="username" placeholder="username" maxlength="100">
    <input type="password" name="password" placeholder="password">
    <input type="password" name="password_again" placeholder="password again">
    <button type="submit">sign up</button>
  </form>
  <h2>log in</h2>
% if log_in_error:
  <p>${log_in_error}</p>
% endif
  <form action="${request.route_path("log_in")}" method="post" class="account_form">
    <input type="text" name="username" placeholder="username" maxlength="100">
    <input type="password" name="password" placeholder="password">
    <button type="submit">log in</button>
  </form>
% endif
