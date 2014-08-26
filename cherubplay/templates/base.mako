<!DOCTYPE html>
<html>
<head>
<title>CHERUBPLAY</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/cherubplay.css?18">
</head>
<body>

<header>
  <h1><a href="${request.route_path("home")}"><img src="/static/logo.png" alt="CHERUBPLAY"></a></h1>
</header>

% if request.user:
  <nav id="nav">
    <ul>
      <li><a href="${request.route_path("home")}" id="nav_home">Home</a></li>
      <li><a href="${request.route_path("chat_list")}" id="nav_chat_list"\
% if request.unread_chats>0:
 data-unread="${request.unread_chats}">Your chats (${request.unread_chats} unread)\
% else:
>Your chats\
% endif
</a></li>
      <li><a href="${request.route_path("account")}" id="nav_account">${request.user.username}</a></li>
      <li><form action="${request.route_path("log_out")}" method="post"><button type="submit" id="nav_log_out">Log out</button></form></li>
    </ul>
  </nav>
% elif request.matched_route.name!="home":
% if "cherubplay.read_only" not in request.registry.settings:
  <nav id="nav">
    <ul>
      <li><a href="${request.route_path("home")}" id="nav_home">Sign up / Log in</a></li>
    </ul>
  </nav>
% endif
% endif

<main>
${next.body()}\
</main>

<script src="//code.jquery.com/jquery-2.0.3.min.js"></script>
<script src="/static/cherubplay.js?6"></script>
<%block name="scripts"></%block>

</body>
</html>

