<%inherit file="base.mako" />\
<%block name="title">Delete ${request.context.title} - </%block>
<%block name="body_class">layout2</%block>
<% from cherubplay.lib import prompt_categories, prompt_starters, prompt_levels %>
<h2>Delete ${request.context.title}</h2>

<main class="flex">
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    <p>Are you sure you want to delete this prompt?</p>
    <section class="tile2">
      <p class="subtitle">${prompt_categories[request.context.category] if request.context.category else "<span class=\"error\">Category not set</span>"|n}, ${prompt_starters[request.context.starter]}, ${prompt_levels[request.context.level]}, written ${request.user.localise_time(request.context.created).strftime("%a %d %b %Y")}.</p>
      <p style="color: #${request.context.colour};">${request.context.text}</p>
    </section>
    <form class="actions" action="${request.route_path("delete_prompt", id=request.context.id)}" method="post">
      <div class="right"><button type="submit">Delete prompt</button></div>
    </form>
  </div>
</main>
