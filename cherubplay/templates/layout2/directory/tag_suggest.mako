<%inherit file="base.mako" />\
<%block name="heading">Suggest changes to "${request.context.tags[0].type.ui_value}:${request.context.tags[0].name}"</%block>
  <p>Here, you can help improve Cherubplay's tagging system by suggesting changes to how the tags are organised.</p>
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
