<%inherit file="chat_base.mako" />\
<%block name="title">\
% if export and export.filename:
Export complete - \
% else:
Export - \
% endif
${own_chat_user.display_title} - \
</%block>
    % if export and export.filename:
      <section class="tile2">
        <h3>Export complete</h3>
        <p>This chat was exported on ${request.user.localise_time(export.generated).strftime("%Y-%m-%d at %H:%M")}.</p>
        <p>Please download it soon - it will expire on ${request.user.localise_time(export.expires).strftime("%Y-%m-%d at %H:%M")}.</p>
        <div class="middle_actions">
          <a href="${request.registry.settings["export.url"]}/${export.file_path}">Download</a>
        </div>
      </section>
    % elif export:
      <section class="tile2">
        <h3>Export in progress</h3>
        <p>Please wait while we export this chat. It could take a few minutes.</p>
      </section>
    % else:
      <form class="tile2" action="${request.route_path("chat_export", url=request.context.chat.url)}" method="POST">
        <h3>Export this chat</h3>
        <p>Here, you can export and then download this chat.</p>
        <div class="middle_actions">
          <button type="submit">Begin export</button>
        </div>
      </form>
    % endif
<%block name="scripts">
  % if export and not export.filename:
    <script>cherubplay.export("${request.matchdict["url"]}");</script>
  % endif
</%block>
