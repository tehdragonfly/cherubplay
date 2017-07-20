<%inherit file="base.mako" />\
<% from cherubplay.models import Tag %>
<%block name="heading">Search</%block>
    % if tags:
      <p>There are multiple tags called <strong>${tags[0].name}</strong>.</p>
      <section class="tile2">
        <ul class="tag_list">
          % for tag in tags:
            % if tag.synonym_of:
              <li>
                ${tag.type.ui_value}:${tag.name}
                (synonym of <a href="${request.route_path("directory_tag", tag_string=(request.context.tag_string_plus(tag.synonym_of) if request.matched_route.name == "directory_tag_search" else tag.synonym_of.tag_string))}">${tag.synonym_of.type.ui_value}:${tag.synonym_of.name}</a>)
              </li>
            % else:
              <li><a href="${request.route_path("directory_tag", tag_string=(request.context.tag_string_plus(tag) if request.matched_route.name == "directory_tag_search" else tag.tag_string))}">${tag.type.ui_value}:${tag.name}</a></li>
            % endif
          % endfor
        </ul>
      </section>
    % else:
      <p>No tags were found for this search.</p>
    % endif
