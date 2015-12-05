<%inherit file="base.mako" />\
<%block name="title">Delete ${request.context.title} - </%block>
<%block name="body_class">layout2</%block>
<h2>Delete ${request.context.title}</h2>

<main class="flex">
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    <p>Are you sure you want to delete this prompt?</p>
    <section class="tile2">
      <p class="subtitle">${prompt_categories[request.context.category]}, ${prompt_levels[request.context.level]}, written ${request.user.localise_time(request.context.created).strftime("%a %d %b %Y")}.</p>
      <p style="color: #${request.context.colour};">${request.context.text}</p>
    </section>
    <form class="actions" action="${request.route_path("delete_prompt", id=request.context.id)}" method="post">
      <div class="right"><button type="submit">Delete prompt</button></div>
    </form>
  </div>
</main>
