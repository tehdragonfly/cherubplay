<%inherit file="base.mako" />\
<%block name="title">Your prompts - </%block>
<%block name="body_class">layout2</%block>
<%
    from cherubplay.lib import make_paginator
    paginator = make_paginator(request, prompt_count, current_page)
%>
<h2>Your prompts</h2>
<main class="flex">
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    <p>Here, you can write your prompts and save them for later. <a href="${request.route_path("new_prompt")}">Write a new prompt</a>.</p>
% if len(prompts)==0:
    <p>You have no prompts.</p>
% else:
    % if paginator.page_count!=1:
    <p class="pager tile2">
      ${paginator.pager(format='~5~')|n}
    </p>
    % endif
    <ul id="chat_list">
    % for prompt in prompts:
      <li class="tile2">
        <h3><a href="${request.route_path("prompt", id=prompt.id)}">${prompt.title}</a></h3>
        <p class="subtitle">${prompt_categories[prompt.category]}, ${prompt_starters[prompt.starter]}, ${prompt_levels[prompt.level]}, written ${request.user.localise_time(prompt.created).strftime("%a %d %b %Y")}.</p>
        % if len(prompt.text) <= 250:
        <p style="color: #${prompt.colour};">${prompt.text}</p>
        % else:
        <div class="expandable">
          <a class="toggle" href="${request.route_path("prompt", id=prompt.id)}">(more)</a>
          <p class="expanded_content" style="color: #${prompt.colour};" data-href="${request.route_path("prompt_ext", ext="json", id=prompt.id)}" data-type="prompt"></p>
          <p class="collapsed_content" style="color: #${prompt.colour};">${prompt.text[:250]}...</p>
        </div>
        % endif
      </li>
    % endfor
    </ul>
    % if paginator.page_count!=1:
    <p class="pager tile2">
      ${paginator.pager(format='~5~')|n}
    </p>
    % endif
  % endif
  </div>
</main>
