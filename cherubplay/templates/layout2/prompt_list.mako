<%inherit file="base.mako" />\
<%block name="title">Your prompts - </%block>
<%block name="body_class">layout2</%block>
<%
    from cherubplay.lib import make_paginator, prompt_categories, prompt_starters, prompt_levels
    paginator = make_paginator(request, prompt_count, current_page)
%>
<h2>Your prompts</h2>
<main class="flex">
  <div class="side_column"></div>
  <div class="side_column"></div>
  <div id="content">
    <p>
      Here, you can write your prompts and save them for later.
      % if "shutdown.prompts" not in request.registry.settings:
        <a href="${request.route_path("new_prompt")}">Write a new prompt</a>.
      % endif
    </p>
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
        <p class="subtitle">${prompt_categories[prompt.category] if prompt.category else "<span class=\"error\">Category not set</span>"|n}, ${prompt_starters[prompt.starter]}, ${prompt_levels[prompt.level]}, written ${request.user.localise_time(prompt.created).strftime("%a %d %b %Y")}.</p>
        <% was_trimmed, preview_text = prompt.text.trim_html(250) %>
        % if not was_trimmed:
          <div class="message" style="color: #${prompt.colour};">${preview_text}</div>
        % else:
          <div class="expandable">
            <a class="toggle" href="${request.route_path("prompt", id=prompt.id)}">(more)</a>
            <div class="expanded_content message" style="color: #${prompt.colour};" data-href="${request.route_path("prompt_ext", ext="json", id=prompt.id)}" data-type="prompt"></div>
            <div class="collapsed_content message" style="color: #${prompt.colour};">${preview_text}</div>
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
