<%inherit file="base.mako" />\
<%block name="heading">Directory</%block>
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
          % for tag in tags_by_type["type"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
        </ul>
        % if tags_by_type["character"] or tags_by_type["fandom"] or tags_by_type["gender"]:
        <h3>Playing:</h3>
        <ul class="tag_list">
          % for tag in tags_by_type["character"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
          % for tag in tags_by_type["fandom"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
          % for tag in tags_by_type["gender"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
        </ul>
        % endif
        % if tags_by_type["character_wanted"] or tags_by_type["fandom_wanted"] or tags_by_type["gender_wanted"]:
        <h3>Looking for:</h3>
        <ul class="tag_list">
          % for tag in tags_by_type["character_wanted"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
          % for tag in tags_by_type["fandom_wanted"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
          % for tag in tags_by_type["gender_wanted"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
        </ul>
        % endif
        % if tags_by_type["misc"]:
        <h3>Other tags:</h3>
        <ul class="tag_list">
          % for tag in tags_by_type["misc"]:
          <li><a href="${request.route_path("directory_tag", type=tag["type"], name=tag["name"])}">${tag["alias"]}</a></li>
          % endfor
        </ul>
        % endif
        % if rq.scenario:
        <hr>
        <p>${rq.scenario}</p>
        % endif
        % if rq.prompt:
        <hr>
        <p style="color: #${rq.colour};">${rq.prompt}</p>
        % endif
      </li>
      % endfor
    </ul>
