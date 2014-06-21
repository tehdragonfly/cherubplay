<!DOCTYPE html>
<html>
<head>
<title>CHERUBPLAY</title>
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="stylesheet" href="/static/cherubplay.css?14">
</head>
<body>
<header>
% if request.user:
  <nav>
    <p><a href="${request.route_path("account")}">${request.user.username}</a></p>
    <a href="${request.route_path("chat_list")}">Your chats\
% if request.unread_chats>0:
 (${request.unread_chats} unread)\
% endif
</a>
    <form action="${request.route_path("log_out")}" method="post"><button type="submit">Log out</button></form>
  </nav>
% elif request.matched_route.name!="home":
% if "cherubplay.read_only" not in request.registry.settings:
  <nav>
    <p><a href="${request.route_path("home")}">Sign up / Log in</a></p>
  </nav>
% endif
% endif
  <h1><a href="${request.route_path("home")}"><img src="/static/logo.png" alt="CHERUBPLAY"></a></h1>
  <br class="clear">
</header>

<main>
${next.body()}\
</main>

<script src="//code.jquery.com/jquery-2.0.3.min.js"></script>
<script src="/static/cherubplay.js?4"></script>
<%block name="scripts"></%block>

</body>
</html>

