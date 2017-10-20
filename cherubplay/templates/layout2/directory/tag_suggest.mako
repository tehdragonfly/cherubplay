<%inherit file="base.mako" />\
<%block name="heading">Suggest changes to "${request.context.tags[0].type.ui_value}:${request.context.tags[0].name}"</%block>
<% from cherubplay.models import Tag %>
<% from cherubplay.models.enums import TagType %>
  <p>Here, you can help improve Cherubplay's tagging system by suggesting changes to how the tags are organised.</p>
  <form class="tile2 tag_form" action="${request.route_path("directory_tag_suggest_make_synonym", **request.matchdict)}" method="post">
    <h3>Make this a synonym</h3>
    % if make_synonym:
      <p>You suggested making this tag a synonym of <a href="${request.route_path("directory_tag", tag_string=make_synonym.target.tag_string)}">${make_synonym.target.type.ui_value}:${make_synonym.target.name}</a>.</p>
    % else:
      <select name="tag_type">
        % for tag_type in Tag.type.type.python_type:
          % if tag_type in (TagType.maturity, TagType.type):
            <% pass %>
          % else:
            <option value="${tag_type.value}">${tag_type.ui_value}</option>
          % endif
        % endfor
      </select>
      <input type="text" name="name" maxlength="100" required>
      <div class="actions">
        <div class="right"><button type="submit">Make synonym</button></div>
      </div>
    % endif
  </form>
  <section class="tile2">
    <h3>Add a parent tag</h3>
    % if parent_tags:
      <p>This tag has the following parents:</p>
      <ul>
        % for parent in parent_tags:
          <li><a href="${request.route_path("directory_tag", tag_string=parent.parent.tag_string)}">${parent.parent.type.ui_value}:${parent.parent.name}</a></li>
        % endfor
      </ul>
    % endif
    % if add_parent:
      <p>You've suggested the following new parents:</p>
      <ul>
        % for suggestion in add_parent:
          <li><a href="${request.route_path("directory_tag", tag_string=suggestion.target.tag_string)}">${suggestion.target.type.ui_value}:${suggestion.target.name}</a></li>
        % endfor
      </ul>
    % endif
    <select name="tag_type">
      % for tag_type in Tag.type.type.python_type:
        % if tag_type in (TagType.maturity, TagType.type):
          <% pass %>
        % else:
          <option value="${tag_type.value}">${tag_type.ui_value}</option>
        % endif
      % endfor
    </select>
    <input type="text" name="name" maxlength="100" required>
    <div class="actions">
      <div class="right"><button type="submit">Add parent</button></div>
    </div>
  </section>
  <form class="tile2" action="${request.route_path("directory_tag_suggest_bump_maturity", **request.matchdict)}" method="post">
    <h3>Restrict to NSFW extreme</h3>
    % if request.context.tags[0].bump_maturity:
      <p>This tag is restricted to the NSFW extreme maturity level. Any requests which have this tag will automatically be placed under NSFW extreme.</p>
    % elif set_bump_maturity:
      <p>You suggested restricting this tag to the NSFW extreme maturity level.</p>
    % else:
      <p>Some tags (such as content warnings for extreme subjects) are restricted to the NSFW extreme maturity level. Any requests which have this tag will automatically be placed under NSFW extreme.</p>
      <div class="actions">
        <div class="right"><button type="submit">Restrict to NSFW extreme</button></div>
      </div>
    % endif
  </form>
