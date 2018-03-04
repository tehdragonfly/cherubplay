<%inherit file="../base.mako" />\
<%block name="title">News - </%block>
<%block name="body_class">layout2</%block>
<h2>News</h2>
<main class="flex"></div>
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    <form class="tile2" action="${request.route_path("admin_news")}" method="post">
      <textarea class="full" name="news" placeholder="News...">${current_news}</textarea>
      <div class="actions">
        <div class="right"><button type="submit">Save</button></div>
      </div>
    </form>
  </div>
</main>
