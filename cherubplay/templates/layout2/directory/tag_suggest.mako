<%inherit file="base.mako" />\
<% from cherubplay.models.enums import TagSuggestionType %>
<%block name="heading">Suggest changes to "${request.context.tags[0].type.ui_value}:${request.context.tags[0].name}"</%block>
  <p>Here, you can help improve Cherubplay's tagging system by suggesting changes to how the tags are organised.</p>
  <form class="tile2" action="${request.current_route_path()}" method="post">
    <h3>Restrict to NSFW extreme</h3>
    % if request.context.tags[0].bump_maturity:
      <p>This tag is restricted to the NSFW extreme maturity level. Any requests which have this tag will automatically be placed under NSFW extreme.</p>
    % elif TagSuggestionType.set_bump_maturity in existing_suggestions:
      <p>You suggested restricting this tag to the NSFW extreme maturity level.</p>
    % else:
      <p>Some tags (such as content warnings for extreme subjects) are restricted to the NSFW extreme maturity level. Any requests which have this tag will automatically be placed under NSFW extreme.</p>
      <input type="hidden" name="type" value="set_bump_maturity">
      <div class="actions">
        <div class="right"><button type="submit">Restrict to NSFW extreme</button></div>
      </div>
    % endif
  </form>
