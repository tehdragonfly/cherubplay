<!DOCTYPE html>
<html>
<head>
<title>CHERUBPLAY</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/cherubplay.css?17">
</head>
<body>

<header>
  <h1><a href="${request.route_path("home")}"><img src="/static/logo.png" alt="CHERUBPLAY"></a></h1>
</header>

% if request.user:
  <nav id="nav">
    <ul>
      <li><a href="${request.route_path("home")}">Home</a></li>
      <li><a href="${request.route_path("account")}">${request.user.username}</a></li>
      <li><a href="${request.route_path("chat_list")}">Your chats\
% if request.unread_chats>0:
 (${request.unread_chats} unread)\
% endif
</a></li>
      <li><form action="${request.route_path("log_out")}" method="post"><button type="submit">Log out</button></form></li>
    </ul>
  </nav>
% elif request.matched_route.name!="home":
% if "cherubplay.read_only" not in request.registry.settings:
  <nav id="nav">
    <ul>
      <li><a href="${request.route_path("home")}">Sign up / Log in</a></li>
    </ul>
  </nav>
% endif
% endif

<main>
${next.body()}\
</main>

<script src="//code.jquery.com/jquery-2.0.3.min.js"></script>
<script src="/static/cherubplay.js?5"></script>
<%block name="scripts"></%block>

</body>
</html>

