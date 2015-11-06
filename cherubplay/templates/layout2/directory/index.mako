<%inherit file="/layout2/base.mako" />\
<%block name="title">Directory - </%block>
<%block name="body_class">layout2</%block>
<h2>Directory</h2>
<main class="flex">
  <div class="side_column">
  </div>
  <div class="side_column">
  </div>
  <div id="content">
    <ul id="chat_list">
      % for rq in requests:
      <% tags_by_type = rq.tags_by_type() %>
      <li class="tile2 request">
        <ul class="tag_list">
          % for tag in tags_by_type["maturity"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
          % for tag in tags_by_type["trigger"]:
          <li class="trigger"><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
        </ul>
        <h3>Playing:</h3>
        <ul class="tag_list">
          % for tag in tags_by_type["fandom"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
          % for tag in tags_by_type["gender"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
          % for tag in tags_by_type["character"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
        </ul>
        <h3>Looking for:</h3>
        <ul class="tag_list">
          % for tag in tags_by_type["fandom_wanted"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
          % for tag in tags_by_type["gender_wanted"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
          % for tag in tags_by_type["character_wanted"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
        </ul>
        <h3>Other tags:</h3>
        <ul class="tag_list">
          % for tag in tags_by_type["misc"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
        </ul>
        <hr>
        <p>${rq.scenario}</p>
        <hr>
        <p style="color: #${rq.colour};">${rq.prompt}</p>
      </li>
      % endfor
    </ul>
  </div>
</main>
