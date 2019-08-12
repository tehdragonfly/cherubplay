<%inherit file="base.mako" />\
<%block name="heading">Export your account data</%block>
  % if export and export.filename:
    <section class="tile2">
      <h3>Export complete</h3>
      <p>Your account data was exported on ${request.user.localise_time(export.generated).strftime("%Y-%m-%d at %H:%M")}.</p>
      <p>Please download it soon - it will expire on ${request.user.localise_time(export.expires).strftime("%Y-%m-%d at %H:%M")}.</p>
      <div class="middle_actions">
        <a href="${request.registry.settings["export.url"]}/${export.file_path}">Download</a>
      </div>
    </section>
  % elif export:
    <section class="tile2">
      <h3>Export in progress</h3>
      <p>Please wait while we export your account data. It could take a few minutes.</p>
    </section>
  % else:
    <form class="tile2" action="${request.route_path("account_export")}" method="POST">
      <p>Here, you can export and then download all of your account data, including your chats, your prompts and your directory requests.</p>
      <div class="middle_actions">
        <button type="submit">Begin export</button>
      </div>
    </form>
  % endif
<%block name="scripts">
  % if export and not export.filename:
    <script>cherubplay.user_export();</script>
  % endif
</%block>
